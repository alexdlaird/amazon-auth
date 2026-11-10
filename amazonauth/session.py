__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import urlparse

import requests
import requests.adapters
from requests import Response, Session
from requests.utils import dict_from_cookiejar

from amazonauth.conf import AmazonAuthConfig, cookies_file_lock, debug_output_file_lock
from amazonauth.exception import (AmazonAuthSignInError, AmazonAuthError, AmazonAuthRedirectError,
                                  AmazonAuthChallengeUnsolvedError)
from amazonauth.forms import (AuthForm, AcicAuthBlocker, CaptchaForm, JSAuthBlocker, MfaDeviceSelectForm, MfaForm,
                              SignInForm, ClaimForm, IntentForm, PasskeyForm)
from amazonauth.util import AmazonSessionResponse, load_class, make_private_dirs, select_one, write_private_file

logger = logging.getLogger(__name__)


class IODefault:
    """
    Handles input/output from the application. By default, this uses console commands, but
    this class exists so that it can be overridden when constructing an :class:`AmazonSession`
    if input/output should be handled another way.
    """

    def echo(self,
             msg: str,
             **kwargs: Any) -> None:
        """
        Echo a message to the console.

        :param msg: The data to send to output.
        :param kwargs: Unused by the default implementation.
        """
        print(msg)

    def prompt(self,
               msg: str,
               type: Optional[Any] = None,
               **kwargs: Any) -> Any:
        """
        Prompt to the console for user input.

        :param msg: The data to use as the input prompt.
        :param type: Unused by the default implementation.
        :param kwargs: Unused by the default implementation.
        :return: The user input result.
        """
        for choice in kwargs.get("choices", []):
            self.echo(choice, **kwargs)

        return input(f"--> {msg}: ")


class RedirectGuardSession(Session):
    """
    A :class:`requests.Session` that follows redirects only where it's safe to: never to ``http``, never re-sending
    a request's data (like a sign-in form, with its password) to another site, and without the ``Origin`` and
    ``Referer`` that name the Amazon page it came from when it leaves the site.
    """

    def rebuild_auth(self,
                     prepared_request: requests.PreparedRequest,
                     response: Response) -> None:
        super().rebuild_auth(prepared_request, response)

        destination = urlparse(prepared_request.url)
        if destination.scheme != "https":
            raise AmazonAuthError(f"Refused to follow a redirect from {response.url} to {prepared_request.url}, "
                                  "which isn't over https.")

        if not self._is_same_site(urlparse(response.url).hostname, destination.hostname):
            if prepared_request.body is not None:
                raise AmazonAuthError(f"Refused to follow a redirect from {response.url} to {prepared_request.url}, "
                                      "which would send the request's data to another site.")
            for header in ("Origin", "Referer"):
                prepared_request.headers.pop(header, None)

    @staticmethod
    def _is_same_site(origin_host: Optional[str],
                      destination_host: Optional[str]) -> bool:
        site = (origin_host or "").lower().removeprefix("www.")
        host = (destination_host or "").lower()
        return bool(site) and (host == site or host.endswith(f".{site}"))


class AmazonSession:
    """
    An interface for interacting with Amazon and authenticating an underlying :class:`requests.Session`. Utilizing
    this class means session data is maintained between requests. Session data may also persisted after each request,
    so it can also be maintained between separate instantiations of the class or application.

    To get started, call the :func:`login` function.
    """

    #: The config class built when no ``config`` is given.
    CONFIG_CLASS: Type[AmazonAuthConfig] = AmazonAuthConfig

    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 debug: bool = False,
                 io: IODefault = IODefault(),
                 config: Optional[AmazonAuthConfig] = None,
                 auth_forms: Optional[List] = None,
                 otp_secret_key: Optional[str] = None,
                 domain: Optional[str] = None) -> None:
        if not config:
            config = self.CONFIG_CLASS(data={"domain": domain} if domain else None)
        elif domain:
            config.set_domain(domain)
        if not auth_forms:
            auth_forms = self.default_auth_forms(config)
            custom_forms = []
            for path in config.auth_forms_classes or []:
                try:
                    module_path, class_name = path.rsplit(".", 1)
                    cls = load_class(module_path.split("."), class_name)
                except (ImportError, AttributeError, ValueError) as e:
                    raise AmazonAuthError(
                        f"Could not load auth_forms_classes entry \"{path}\": {e}"
                    ) from e
                if not (isinstance(cls, type) and issubclass(cls, AuthForm)):
                    raise AmazonAuthError(
                        f"auth_forms_classes entry \"{path}\" must be a subclass of "
                        f"{AuthForm.__module__}.{AuthForm.__name__}."
                    )
                # AuthForm subclasses registered via auth_forms_classes are expected to take
                # only ``config`` (e.g. AwsWafForm subclasses); the base AuthForm signature
                # additionally requires ``selector``.
                custom_forms.append(cls(config))  # type: ignore[call-arg]
            # Insert as a block before the blocker pair (AcicAuthBlocker, JSAuthBlocker)
            # so that solver forms run first while preserving auth_forms_classes order.
            insert_pos = len(auth_forms) - 2
            for offset, form_instance in enumerate(custom_forms):
                auth_forms.insert(insert_pos + offset, form_instance)

        #: An Amazon username. Environment variable ``AMAZON_USERNAME`` will override passed in or config value.
        self.username: Optional[str] = config.environment_value("username") or username or config.username
        #: An Amazon password. Environment variable ``AMAZON_PASSWORD`` will override passed in or config value.
        self.password: Optional[str] = config.environment_value("password") or password or config.password
        #: The secret key Amazon provides when manually adding a 2FA authenticator app. Setting this will allow
        #: one-time password challenges to be auto-solved. Environment variable ``AMAZON_OTP_SECRET_KEY`` will override
        #: passed in or config value.
        self.otp_secret_key: Optional[str] = (config.environment_value("otp_secret_key") or otp_secret_key or
                                              config.otp_secret_key)

        #: Setting logger to ``DEBUG`` will send output to ``stderr`` and write an HTML file for all requests made
        #: on the session.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        #: The I/O handler for echoes and prompts.
        self.io: IODefault = io
        #: The config to use.
        self.config: AmazonAuthConfig = config
        #: The list of form implementations to use with authentication. If a value is passed for this when
        #: instantiating an AmazonSession, ensure that list is populated with the default form implementations.
        #: :func:`~amazonauth.session.AmazonSession.default_auth_forms` returns the default chain so callers can
        #: extend it instead of duplicating it.
        self.auth_forms: List[AuthForm] = auth_forms

        #: The shared session to be used across all requests.
        self.session: Session = self._create_session()
        #: If :func:`login` has been executed and successfully logged in the session.
        self.is_authenticated: bool = False
        self._sign_in_required: bool = False
        self._cookie_jar_mtime: Optional[float] = None

        with cookies_file_lock:
            make_private_dirs(os.path.dirname(self.config.cookie_jar_path))

            if os.path.exists(self.config.cookie_jar_path):
                with open(self.config.cookie_jar_path, "r", encoding="utf-8") as f:
                    self._cookie_jar_mtime = os.fstat(f.fileno()).st_mtime
                    self._load_cookie_jar_data(json.loads(f.read()))
            else:
                self._load_shared_cookie_jar()

    @property
    def cookie_jar_mtime(self) -> Optional[float]:
        """
        The modification time of the persisted cookie jar when this session last loaded or saved it, or ``None`` if
        there was no jar then. If the file's modification time no longer matches, another process has saved it since.
        """
        return self._cookie_jar_mtime

    @staticmethod
    def default_auth_forms(config: AmazonAuthConfig) -> List[AuthForm]:
        """
        Build the default ordered list of :class:`~amazonauth.forms.AuthForm` instances used by
        :class:`AmazonSession`. Callers wishing to inject a custom form (e.g. a third-party WAF
        Captcha solver) can call this and insert their own handler before passing the list as
        ``auth_forms``.

        :param config: The config to bind to each form.
        :return: The default ordered list of :class:`~amazonauth.forms.AuthForm` instances.
        """
        return [ClaimForm(config),
                IntentForm(config),
                SignInForm(config),
                PasskeyForm(config),
                MfaDeviceSelectForm(config),
                MfaForm(config),
                CaptchaForm(config),
                CaptchaForm(config,
                            config.selectors.CAPTCHA_2_FORM_SELECTOR,
                            config.selectors.CAPTCHA_2_ERROR_SELECTOR,
                            "field-keywords"),
                MfaForm(config,
                        config.selectors.CAPTCHA_OTP_FORM_SELECTOR),
                AcicAuthBlocker(config),
                JSAuthBlocker(config,
                              config.constants.JS_ROBOT_TEXT_REGEX,
                              config.constants.AKAMAI_INTERSTITIAL_REGEX)]

    def request(self,
                method: str,
                url: str,
                persist_cookies: Optional[bool] = None,
                binary: bool = False,
                **kwargs: Any) -> AmazonSessionResponse:
        """
        Execute the request against Amazon with base headers, parsing and storing the response.

        :param method: The request method to execute.
        :param url: The URL to execute ``method`` on.
        :param persist_cookies: If ``True``, cookies from the response will be persisted to a file, and if ``False``,
            they won't be. By default, they're persisted when the response changed them, unless another process has
            saved the file since this session did, so a stale session can't overwrite a newer sign-in.
        :param binary: ``True`` if the response is a file, like a PDF, rather than a page. It is not parsed as HTML,
            and ``debug`` mode doesn't write it to a page file.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`requests.request`.
        :return: The response from the executed request.
        """
        headers = {**self.config.constants.BASE_HEADERS, **(kwargs.get("headers") or {})}
        kwargs["headers"] = {name: value for name, value in headers.items() if name.lower() != "host"}

        if self.debug:
            logger.debug(f"{method} request: {url}")

        if self.config.request_timeout is not None:
            kwargs.setdefault("timeout", self.config.request_timeout)

        self._set_request_cookies()
        cookie_jar_data = self._cookie_jar_data()

        try:
            response = self.session.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise AmazonAuthError(f"The page {url} returned no response: {e}. Amazon had an issue on their end, "
                                  "or may be temporarily blocking your requests. Wait a bit before trying "
                                  "again.") from e
        except requests.RequestException as e:
            raise AmazonAuthError(f"The page {url} returned no response: {e}.") from e
        amazon_session_response = AmazonSessionResponse(response,
                                                        self.config.bs4_parser,
                                                        binary=binary)

        if persist_cookies is None:
            persist_cookies = self._cookie_jar_data() != cookie_jar_data and self._cookie_jar_unchanged_on_disk()
        if persist_cookies:
            with cookies_file_lock:
                self._write_cookie_jar()

        if self.debug:
            final_url = amazon_session_response.response.url
            url_str = ""
            if amazon_session_response.response.history:
                url_str = f" - (redirected) {final_url}"
            elif final_url != url:
                url_str = f" - {final_url}"
            logger.debug(f"Response: {amazon_session_response.response.status_code}{url_str}")

            if not binary:
                make_private_dirs(self.config.output_dir)
                page_path = os.path.join(self.config.output_dir,
                                         self._get_page_from_url(self.config.output_dir,
                                                                 amazon_session_response.response.url))
                write_private_file(page_path, amazon_session_response.response.text)
                logger.debug(f"Response written to file: {page_path}")

        return amazon_session_response

    def get(self,
            url: str,
            **kwargs: Any) -> AmazonSessionResponse:
        """
        Perform a ``GET`` request.

        :param url: The URL to request.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The response from the executed request.
        """
        return self.request("GET", url, **kwargs)

    def post(self,
             url: str,
             **kwargs: Any) -> AmazonSessionResponse:
        """
        Perform a ``POST`` request.

        :param url: The URL to request.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The response from the executed request.
        """
        return self.request("POST", url, **kwargs)

    def _set_request_cookies(self) -> None:
        request_cookies = self.config.constants.REQUEST_COOKIES
        if not request_cookies:
            return

        domain = urlparse(self.config.constants.BASE_URL).hostname
        with self.session.cookies._cookies_lock:  # type: ignore[attr-defined]
            for cookie in [cookie for cookie in self.session.cookies if cookie.name in request_cookies]:
                self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
            for name, value in request_cookies.items():
                self.session.cookies.set(name, value, domain=domain, path="/")

    def auth_cookies_stored(self) -> bool:
        cookies = dict_from_cookiejar(self.session.cookies)
        for cookie in self.config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            if cookie not in cookies:
                return False
        return True

    def check_session(self,
                      verify: bool = False) -> bool:
        """
        Check if a persisted session exists, meaning requests can be made without needing to provide credentials.

        A session's cookies outlive it, so pass ``verify`` to also ask Amazon whether it still accepts the session.
        This requests the Order history and checks it with :func:`check_response`.

        :param verify: ``True`` to also ask Amazon whether it still accepts the persisted session.
        :return: ``True`` if a persisted session exists and, with ``verify``, Amazon accepts it. ``False`` if none
            exists or, with ``verify``, Amazon redirected to login, so the session needs to sign in again.
        :raises AmazonAuthError: With ``verify``, if Amazon's response wasn't ``ok``, which says nothing about the
            session.
        """
        if not self.auth_cookies_stored():
            return False
        if not verify:
            return True

        logger.debug("Asking Amazon whether it still accepts the persisted session ...")

        orders_response = self.get(self.config.constants.SESSION_CHECK_URL)
        try:
            self.check_response(orders_response)
        except AmazonAuthRedirectError:
            return False

        return True

    def login(self) -> None:
        """
        Execute an Amazon login process. This will include the sign-in page, and may also include OTP (if 2FA is
        enabled for your account), Captcha challenges, and any other forms in
        :attr:`~amazonauth.session.AmazonSession.auth_forms`.

        If successful, ``is_authenticated`` will be set to ``True``.

        A persisted session is reused, unless Amazon redirected one of this session's requests to login, in which
        case it's logged out first, so the login starts fresh.
        """
        if self._sign_in_required:
            self.logout()

        self._provision_cookies()

        last_response = self.get(self.config.constants.SIGN_IN_URL,
                                 params=self.config.constants.SIGN_IN_QUERY_PARAMS)

        self.is_authenticated = False
        form_found = False
        attempts = 0
        while not self.is_authenticated and attempts < self.config.max_auth_attempts:
            greeting = select_one(last_response.parsed, self.config.selectors.NAV_GREETING_SELECTOR)
            if self.auth_cookies_stored() or \
                    (greeting is not None and self.config.constants.SIGNED_OUT_TEXT not in greeting.get_text()):
                self.is_authenticated = True
                break

            if attempts > 0:
                logger.debug(f"Retrying auth flow, attempt {attempts} in "
                             f"{self.config.auth_reattempt_wait} seconds ...")
                time.sleep(self.config.auth_reattempt_wait)

                # If a form was found on the last attempt, then we already have a response to evaluate from that,
                # otherwise (and/or if we were redirected back to the home page) re-start the auth flow for this
                # attempt
                if not form_found or last_response.response.url.rstrip("/") == self.config.constants.BASE_URL:
                    last_response = self.get(self.config.constants.SIGN_IN_URL,
                                             params=self.config.constants.SIGN_IN_QUERY_PARAMS)

                form_found = False

            form_response = self._process_forms(last_response)

            if form_response:
                last_response = form_response
                form_found = True

            if not form_found:
                self._raise_auth_error(last_response.response)

            attempts += 1

        if attempts == self.config.max_auth_attempts:
            raise AmazonAuthSignInError(
                "Sign-in attempts exhausted. If your credentials are correct, "
                "try increasing the max_auth_attempts config value.")

    def logout(self) -> None:
        """
        Logout and close the existing Amazon session and clear cookies.
        """
        self.get(self.config.constants.SIGN_OUT_URL, persist_cookies=True)
        self.session.close()
        self.session = self._create_session()

        with cookies_file_lock:
            self._write_cookie_jar()

        self.is_authenticated = False
        self._sign_in_required = False

    def _cookie_jar_data(self) -> List[Dict[str, Any]]:
        return [{"name": cookie.name, "value": cookie.value, "domain": cookie.domain, "path": cookie.path,
                 "secure": cookie.secure, "expires": cookie.expires} for cookie in self.session.cookies]

    def _load_cookie_jar_data(self,
                              data: Union[Dict[str, str], List[Dict[str, Any]]]) -> None:
        if isinstance(data, dict):
            domain = "." + (urlparse(self.config.constants.BASE_URL).hostname or "").removeprefix("www.")
            data = [{"name": name, "value": value, "domain": domain} for name, value in data.items()]

        for cookie in data:
            self.session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain", ""),
                                     path=cookie.get("path", "/"), secure=cookie.get("secure", False),
                                     expires=cookie.get("expires"))

    def _load_shared_cookie_jar(self) -> None:
        """
        Load the active site's cookies from the jar every site shared before each had its own, if the site has no jar
        of its own yet, so a session saved there still works. The shared jar is left as it is, and the site's
        cookies are persisted to its own jar from then on.
        """
        shared_cookie_jar_path = self.config.shared_cookie_jar_path
        if not shared_cookie_jar_path or not os.path.exists(shared_cookie_jar_path):
            return

        with open(shared_cookie_jar_path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())

        if isinstance(data, list):
            data = [cookie for cookie in data if self._is_site_cookie(cookie)]
            if not data:
                return

        logger.debug(f"Loading the {self.config.site} session from {shared_cookie_jar_path}, which every site "
                     f"shared, until it is saved to {self.config.cookie_jar_path} ...")
        self._load_cookie_jar_data(data)

    def _is_site_cookie(self,
                        cookie: Dict[str, Any]) -> bool:
        domain = (cookie.get("domain") or "").lstrip(".")
        return domain == self.config.site or domain.endswith(f".{self.config.site}")

    def _write_cookie_jar(self) -> None:
        write_private_file(self.config.cookie_jar_path, json.dumps(self._cookie_jar_data()))
        self._cookie_jar_mtime = self._read_cookie_jar_mtime()

    def _read_cookie_jar_mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(self.config.cookie_jar_path)
        except OSError:
            return None

    def _cookie_jar_unchanged_on_disk(self) -> bool:
        return self._read_cookie_jar_mtime() == self._cookie_jar_mtime

    def build_response_error(self,
                             response: Response) -> str:
        """
        Build an error message from the given response.

        :param response: The response to check and build a response.
        :return: The error message.
        """
        error_msg = f"The page {response.url} returned {response.status_code}."
        if 500 <= response.status_code < 600:
            error_msg += (" Amazon had an issue on their end, or may be temporarily blocking your requests. "
                          "Wait a bit before trying again.")
        return error_msg

    def check_response(self,
                       amazon_session_response: AmazonSessionResponse,
                       meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Check the response to ensure it appears to be returning a valid response, and that it is still authenticated.
        We detect if authentication has expired by checking for redirects to the login page. Raise an error if the
        response is not going to contain the requested data for parsing.

        A redirect to the login page doesn't log the session out, since Amazon asks some pages to confirm a sign-in
        that isn't recent enough while the session's other pages keep working. Calling :func:`login` after one logs
        out first, so it signs in again.

        :param amazon_session_response: The response to check.
        :param meta: Metadata to be added to any errors raised.
        """
        if not amazon_session_response.response.ok:
            raise AmazonAuthError(self.build_response_error(amazon_session_response.response), meta=meta)
        if (amazon_session_response.response.url.startswith(self.config.constants.SIGN_IN_URL) or
                (amazon_session_response.parsed and
                 amazon_session_response.parsed.select_one(self.config.selectors.SIGN_IN_FORM_SELECTOR) is not None)):
            redirect_url = amazon_session_response.response.url
            logger.debug(f"Amazon redirected to login at {redirect_url}, so the persisted session needs to sign in "
                         f"again.")
            self._sign_in_required = True
            raise AmazonAuthRedirectError("Amazon redirected to login. Amazon wants the sign-in confirmed "
                                          "before showing this page, so call AmazonSession.login() to sign in "
                                          "again.",
                                          meta={**(meta or {}), "redirect_url": redirect_url})

    def _get_page_from_url(self,
                           output_dir: str,
                           url: str) -> str:
        page_name = os.path.splitext(os.path.basename(urlparse(url).path))[0]
        if not page_name:
            page_name = "index"

        with debug_output_file_lock:
            i = 0
            filename_frmt = "{page_name}_{index}.html"
            while os.path.isfile(os.path.join(output_dir, filename_frmt.format(page_name=page_name, index=i))):
                i += 1
        return filename_frmt.format(page_name=page_name, index=i)

    def _raise_auth_error(self,
                          response: Response) -> None:
        if response.ok:
            error_msg = (f"This is an unknown page, or its parsed contents don't match a "
                         f"known sign-in flow. {response.url}")
        else:
            error_msg = self.build_response_error(response)

        if not self.debug:
            error_msg += "\n--> To capture the page to a file, set AmazonSession.debug=True."

        raise AmazonAuthSignInError(error_msg)

    def _create_session(self) -> Session:
        session = RedirectGuardSession()
        adapter = requests.adapters.HTTPAdapter(pool_connections=self.config.connection_pool_size,
                                                pool_maxsize=self.config.connection_pool_size)
        session.mount('https://', adapter)
        return session

    def _process_forms(self,
                       last_response: AmazonSessionResponse) -> Optional[AmazonSessionResponse]:
        unsolved: Optional[AmazonAuthChallengeUnsolvedError] = None
        for form in self.auth_forms:
            # Once a form couldn't solve the challenge, its error is the one to raise, not a blocker's generic one
            if unsolved and isinstance(form, (AcicAuthBlocker, JSAuthBlocker)):
                continue
            if form.select_form(self, last_response.parsed):
                try:
                    form.fill_form()
                    return form.submit(last_response.response)
                except AmazonAuthChallengeUnsolvedError as e:
                    logger.debug(f"{type(form).__name__} couldn't solve the challenge, trying the next form: {e}")
                    unsolved = e

        if unsolved:
            raise unsolved

        return None

    def _provision_cookies(self) -> None:
        last_response = None
        attempts = 0
        # We have to retry for stability here, to ensure Amazon returns us the desktop version of the site; if we
        # don't implement this logic, Amazon will sometimes return a mobile version of teh site (regardless of
        # User-Agent headers)
        while last_response is None or \
                (last_response.parsed.select_one(self.config.selectors.BAD_INDEX_SELECTOR) is not None
                 and attempts < self.config.max_cookie_attempts):
            if attempts > 0:
                logger.debug(f"Retrying cookie provisioning, attempt {attempts} in "
                             f"{self.config.cookie_reattempt_wait} seconds ...")
                time.sleep(self.config.cookie_reattempt_wait)

            # To provision initial, unauthenticated cookies, fetch the Amazon home page
            last_response = self.get(self.config.constants.BASE_URL)
            # We process forms just in case Amazon presents a Captcha challenge on unauthenticated URLs
            self._process_forms(last_response)

            attempts += 1

        if attempts == self.config.max_cookie_attempts:
            raise AmazonAuthSignInError("Amazon is not returning a parsable home page. Try waiting a while, "
                                        "increasing the max_cookie_attempts config value, or using a different IP "
                                        "address, as this one may be flagged as a bot.")
