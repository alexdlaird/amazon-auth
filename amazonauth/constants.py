__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

from amazonauth.conf import AmazonAuthConfig
from amazonauth.region_data import REGION_SITES

logger = logging.getLogger(__name__)


class AuthConstants:
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonauth.conf import AmazonAuthConfig

        config = AmazonAuthConfig(data={"constants_class": "my_module.MyConstants"})

    URLs and the URL-shaped headers (``Origin``, ``Host``, ``Referer``) are derived from the active
    Amazon domain. ``REQUEST_COOKIES``, ``Accept-Language``, the sign-in
    ``openid.assoc_handle``, and ``COOKIES_SET_WHEN_AUTHENTICATED`` are adjusted for known Amazon sites
    (each only when a subclass has not overridden it). The domain is resolved in this precedence order:

    1. The ``domain`` key on :class:`~amazonauth.conf.AmazonAuthConfig`.
    2. The default, ``amazon.com``.

    ``amazon-auth`` requests Amazon's pages in English from any site known to offer English. Subclass and set
    ``constants_class`` to override any value a site requires.
    """

    ##########################################################################
    # General URL (defaults; overridden in ``__init__`` when a domain is set)
    ##########################################################################

    BASE_URL = "https://www.amazon.com"

    ##########################################################################
    # URLs for AmazonSession
    ##########################################################################

    SIGN_IN_URL = f"{BASE_URL}/ap/signin"
    SIGN_IN_QUERY_PARAMS = {"openid.pape.max_auth_age": "0",
                            "openid.return_to": f"{BASE_URL}/?ref_=nav_custrec_signin",
                            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.assoc_handle": "usflex",
                            "openid.mode": "checkid_setup",
                            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.ns": "http://specs.openid.net/auth/2.0"}
    SIGN_IN_CLAIM_URL = f"{BASE_URL}/ax/claim"
    SIGN_OUT_URL = f"{BASE_URL}/gp/flex/sign-out.html"

    ##########################################################################
    # Headers
    ##########################################################################

    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Host": urlparse(BASE_URL).netloc,
        "Origin": BASE_URL,
        "Referer": f"{SIGN_IN_URL}?{urlencode(SIGN_IN_QUERY_PARAMS)}",
        "Sec-Ch-Ua": '"Chromium";v="149", "Google Chrome";v="149", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",  # noqa: E501
    }
    #: ``BASE_HEADERS`` changes for each ``browser`` that isn't Chromium-based. A ``None`` value removes the header.
    BROWSER_HEADERS: Dict[str, Dict[str, Optional[str]]] = {
        "firefox": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Ch-Ua": None,
            "Sec-Ch-Ua-Mobile": None,
            "Sec-Ch-Ua-Platform": None,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        },
        "webkit": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": None,
            "Sec-Ch-Ua-Mobile": None,
            "Sec-Ch-Ua-Platform": None,
            "Sec-Fetch-User": None,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.6 Safari/605.1.15",  # noqa: E501
        },
    }
    #: Cookies sent with every request to the active Amazon domain, replacing any cookie of the same name Amazon
    #: set, for a site that picks something like its language from a cookie (e.g. ``{"lc-acbde": "de_DE"}`` for
    #: German pages on amazon.de). Left at its default, it's set to the English language cookie of the active site,
    #: if it's known to offer English, unless ``Accept-Language`` in ``BASE_HEADERS`` is overridden.
    REQUEST_COOKIES: Dict[str, str] = {}

    ##########################################################################
    # Authentication
    ##########################################################################

    COOKIES_SET_WHEN_AUTHENTICATED = ["x-main"]
    SIGNED_OUT_TEXT = "Hello, sign in"
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*verify that you're not a robot[.\s\S]*Enable JavaScript[.\s\S]*"
    AKAMAI_INTERSTITIAL_REGEX = r"/_sec/verify\?provider=interstitial"
    GOKU_PROPS_REGEX = r"window\.gokuProps\s*=\s*(\{.*?\});"
    ACIC_CHALLENGE_PATH = "/ax/aaut/verify/ap/challenge"
    WAF_TOKEN_COOKIE = "aws-waf-token"

    def __init__(self,
                 config: Optional[AmazonAuthConfig] = None) -> None:
        if config is not None:
            domain, browser = config.domain, config.browser
        else:
            environment = AmazonAuthConfig.read_environment()
            domain, browser = environment.get("domain"), environment.get("browser")
        if browser:
            self._apply_browser(browser)
        if domain:
            self._apply_domain(domain)
        self._apply_language_cookie(self._tld(self.BASE_URL))

    @classmethod
    def region_auth_cookie(cls,
                           tld: str) -> Optional[str]:
        """
        The cookie that marks an authenticated session on an Amazon site: its language cookie, with ``lc-`` swapped
        for ``x-`` (e.g. ``lc-acbde`` and ``x-acbde``, or ``.com``'s ``lc-main`` and ``x-main``).

        :param tld: The TLD suffix that follows ``amazon.`` (e.g. ``co.uk``).
        :return: The cookie's name, or ``None`` if the site's isn't known.
        """
        site = REGION_SITES.get(tld)
        if not site or not site.language_cookie or not site.language_cookie.startswith("lc-"):
            return None
        return f"x-{site.language_cookie[len('lc-'):]}"

    def _apply_browser(self,
                       browser: str) -> None:
        """
        Apply browser-specific header overrides for the given browser engine. A header a subclass changed from
        the default keeps its value.

        :param browser: The browser that signs in, e.g. ``"chrome"``, ``"msedge"``, ``"firefox"``. A browser not in
            ``BROWSER_HEADERS``, like Chrome or Edge, is Chromium-based, so ``BASE_HEADERS`` is left unchanged.
        """
        browser_headers = self.BROWSER_HEADERS.get(browser)
        if browser_headers is None:
            return
        headers = dict(type(self).BASE_HEADERS)
        for key, value in browser_headers.items():
            if headers.get(key) != AuthConstants.BASE_HEADERS.get(key):
                continue
            if value is None:
                headers.pop(key, None)
            else:
                headers[key] = value
        self.BASE_HEADERS = headers

    def _apply_domain(self,
                      domain: str) -> None:
        """
        Override the URL-derived attributes for the given Amazon domain, and the values that depend on which Amazon
        site it is, from its region data: the sign-in ``openid.assoc_handle`` (Amazon rejects a sign-in, with HTTP 404,
        whose handle doesn't match the site), ``Accept-Language``, and
        ``COOKIES_SET_WHEN_AUTHENTICATED``. Each is applied only when a subclass hasn't overridden it, and a site that
        isn't known keeps the defaults.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL (e.g. ``https://www.amazon.com.au``).
        """
        base_url = self._normalize_base_url(domain)
        tld = self._tld(base_url)
        site = REGION_SITES.get(tld)

        # Build from the instance-level BASE_HEADERS if _apply_browser has already set it;
        # otherwise fall back to the class-level definition.
        sign_in_query_params = dict(type(self).SIGN_IN_QUERY_PARAMS)
        sign_in_query_params["openid.return_to"] = f"{base_url}/?ref_=nav_custrec_signin"
        if (site and site.assoc_handle and
                sign_in_query_params["openid.assoc_handle"] ==
                AuthConstants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"]):
            sign_in_query_params["openid.assoc_handle"] = site.assoc_handle

        sign_in_url = f"{base_url}/ap/signin"

        self.BASE_URL = base_url
        self.SIGN_IN_URL = sign_in_url
        self.SIGN_IN_QUERY_PARAMS = sign_in_query_params
        self.SIGN_IN_CLAIM_URL = f"{base_url}/ax/claim"
        self.SIGN_OUT_URL = f"{base_url}/gp/flex/sign-out.html"

        headers = dict(vars(self).get("BASE_HEADERS", type(self).BASE_HEADERS))
        headers["Origin"] = base_url
        headers["Host"] = urlparse(base_url).netloc
        headers["Referer"] = f"{sign_in_url}?{urlencode(sign_in_query_params)}"
        if site and site.english_locale and self._requests_default_language():
            headers["Accept-Language"] = self._english_accept_language(site.english_locale, headers["Accept-Language"])
        self.BASE_HEADERS = headers

        auth_cookie = self.region_auth_cookie(tld)
        if auth_cookie and type(self).COOKIES_SET_WHEN_AUTHENTICATED == AuthConstants.COOKIES_SET_WHEN_AUTHENTICATED:
            self.COOKIES_SET_WHEN_AUTHENTICATED = [auth_cookie]

    def _apply_language_cookie(self,
                               tld: str) -> None:
        """
        Request English pages from an Amazon site that offers them, by setting its language cookie in
        ``REQUEST_COOKIES``. It's sent with every request, so pages stay English whatever language the account is set
        to. Skipped when a subclass overrides ``REQUEST_COOKIES`` or ``Accept-Language``, so the subclass's own
        language wins.

        :param tld: The TLD suffix that follows ``amazon.`` (e.g. ``co.uk``).
        """
        site = REGION_SITES.get(tld)
        if site and site.english_locale and site.language_cookie and self._requests_default_language():
            self.REQUEST_COOKIES = {site.language_cookie: site.english_locale}

    def _requests_default_language(self) -> bool:
        return (type(self).REQUEST_COOKIES is AuthConstants.REQUEST_COOKIES and
                type(self).BASE_HEADERS.get("Accept-Language") == AuthConstants.BASE_HEADERS.get("Accept-Language"))

    @staticmethod
    def _english_accept_language(locale: str,
                                 default: str) -> str:
        language_tag = locale.replace("_", "-")
        if language_tag == "en-US":
            return default
        return f"{language_tag},en;q=0.9,en-US;q=0.8"

    @staticmethod
    def _tld(base_url: str) -> str:
        host = urlparse(base_url).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[len("www."):]
        return host[len("amazon."):] if host.startswith("amazon.") else ""

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        value = value.strip().rstrip("/")
        if value.startswith(("http://", "https://")):
            return value
        if value.startswith("www."):
            return f"https://{value}"
        return f"https://www.{value}"
