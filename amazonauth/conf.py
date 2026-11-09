__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import inspect
import logging
import os
import threading
from typing import Any, Dict, Optional, Set, Union
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound

from amazonauth import util
from amazonauth.exception import AmazonAuthError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")

config_file_lock = threading.Lock()
cookies_file_lock = threading.Lock()
debug_output_file_lock = threading.Lock()

ENVIRONMENT_VARIABLE_PREFIX = "AMAZON_"

#: The Amazon site whose session is kept in the default ``cookie_jar_path`` itself, rather than in a jar of its own.
DEFAULT_COOKIE_JAR_SITE = "amazon.com"


class AmazonAuthConfig:
    """
    An object containing ``amazon-auth``'s configuration. The state of this object is populated from the config file,
    if present, when it is instantiated, and it is also persisted back to the config file when :func:`~save` is called.

    The config file is ``~/.config/amazonorders/config.yml``, unless another ``config_path`` is given. For instance:

    .. code-block:: yaml

        domain: amazon.co.uk

    If overrides are passed in ``data`` parameter when this object is instantiated, they will be used to populate the
    new object, but not persisted to the config file until :func:`~save` is called.

    Every config value can also be set with an ``AMAZON_<KEY>`` environment variable, for instance
    ``AMAZON_MAX_AUTH_ATTEMPTS=20`` for ``max_auth_attempts``. An environment variable takes precedence over every
    other source, then values passed in code, then the config file, then the defaults. The
    value of a key with a default is read as YAML, as it would be in the config file, and any other value is used
    as-is. Environment variables are never persisted to the config file.
    """

    #: The package named in messages that suggest installing something, e.g. ``pip install amazon-auth[lxml]``.
    PACKAGE_NAME: str = "amazon-auth"
    #: The documentation that messages link to, e.g. for sign-in challenges.
    DOCS_URL: str = "https://amazon-auth.readthedocs.io"
    #: Where messages ask for unexpected behavior to be reported.
    ISSUES_URL: str = "https://github.com/alexdlaird/amazon-auth/issues"

    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> None:
        #: The path to use for the config file.
        self.config_path: str = os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path

        self._data: Dict[str, Any] = self._default_data()
        self._environment: Dict[str, Any] = self.read_environment()
        self._resolved_classes: Dict[str, Any] = {}
        self._assigned_classes: Dict[str, Any] = {}
        self._unavailable_class_paths: Set[str] = set()

        with config_file_lock:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as config_file:
                    logger.debug(f"Loading config from {self.config_path} ...")
                    config = yaml.safe_load(config_file)
                    if config is not None:
                        config.update(data or {})
                        data = config

        # Overload defaults if values passed
        self._data.update(data or {})

        self._validate_bs4_parser()
        self._validate_class_paths()

        #: The :class:`~amazonauth.constants.AuthConstants` in use, rebuilt when the domain changes.
        self.constants: Any

        self._load_classes()

    @classmethod
    def read_environment(cls) -> Dict[str, Any]:
        """
        Read the config values set with ``AMAZON_<KEY>`` environment variables. An empty variable is ignored.

        :return: The config values set in the environment, by config key.
        :raises AmazonAuthError: If the value of a key with a default is not valid YAML.
        """
        default_data = cls._default_data()
        environment = {}
        for name, value in os.environ.items():
            if not name.startswith(ENVIRONMENT_VARIABLE_PREFIX) or not value:
                continue

            key = name[len(ENVIRONMENT_VARIABLE_PREFIX):].lower()
            if key not in default_data:
                environment[key] = value
                continue

            try:
                environment[key] = yaml.safe_load(value)
            except yaml.YAMLError as e:
                raise AmazonAuthError(f"Environment variable {name} is not valid YAML: {e}") from e

        return environment

    def environment_value(self,
                          key: str) -> Any:
        """
        Get the value set for the given config key with its ``AMAZON_<KEY>`` environment variable.

        :param key: The config key.
        :return: The value, or ``None`` if the environment variable isn't set.
        """
        return self._environment.get(key)

    def _get(self,
             key: str) -> Any:
        if key in self._environment:
            return self._environment[key]

        return self._data.get(key)

    @staticmethod
    def _default_data() -> Dict[str, Any]:
        """
        Provision the default config values.

        :return: The default config values.
        """
        thread_pool_size = (os.cpu_count() or 1) * 4
        return {
            # The maximum number of times to retry provisioning initial cookies before failing
            "max_cookie_attempts": 10,
            # The number of seconds to wait before retrying to provision initial cookies
            "cookie_reattempt_wait": 0.5,
            # The maximum number of authentication forms to try before failing
            "max_auth_attempts": 10,
            # The number of seconds to wait before retrying the auth flow
            "auth_reattempt_wait": 5,
            # Where output files (for instance, HTML pages, when ``debug`` mode is enabled) will be written
            "output_dir": os.path.join(os.getcwd(), "output"),
            # The session for ``amazon.com``; every other site's is kept beside it (see :attr:`cookie_jar_path`)
            "cookie_jar_path": AmazonAuthConfig._default_cookie_jar_path(),
            "constants_class": "amazonauth.constants.AuthConstants",
            "selectors_class": "amazonauth.selectors.AuthSelectors",
            "bs4_parser": "html.parser",
            "auth_forms_classes": [],
            # Timeout in seconds for browser-based challenge detection and resolution
            "browser_timeout": 30,
            # Timeout in seconds for HTTP requests; ``None`` leaves requests with no timeout
            "request_timeout": None,
            "connection_pool_size": thread_pool_size * 2,
            # The maximum number of failed attempts to allow before failing CLI authentication
            "max_auth_retries": 1
        }

    @staticmethod
    def _default_cookie_jar_path() -> str:
        return os.path.join(DEFAULT_CONFIG_DIR, "cookies.json")

    def _load_classes(self) -> None:
        """
        Instantiate the constants and selectors, which the auth layer itself uses and so are always
        needed. The entity, output, and Transactions page classes resolve on first use instead.
        """
        self.constants = self._instantiate_constants()
        self.selectors = self._load_configured_class("selectors_class")()

    def _load_configured_class(self,
                               key: str) -> Any:
        """
        Load the class the given config key names. The config file can be shared with other packages built on this
        one, which save their own class paths to it, so a class whose package isn't installed here falls back to the
        default, with a warning. Any other failure to load it is raised.

        :param key: The config key naming the class.
        :return: The class.
        """
        class_path = self._class_path(key)
        module_path, class_name = class_path.rsplit(".", 1)
        try:
            return util.load_class(module_path.split("."), class_name)
        except ModuleNotFoundError as e:
            default_class_path = self._default_data()[key]
            if (class_path == default_class_path or not e.name or
                    not (module_path == e.name or module_path.startswith(f"{e.name}."))):
                raise

            if class_path not in self._unavailable_class_paths:
                self._unavailable_class_paths.add(class_path)
                logger.warning(f"Configured {key} '{class_path}' is unavailable, since '{e.name}' isn't installed; "
                               f"using the default '{default_class_path}'.")
            default_module_path, default_class_name = default_class_path.rsplit(".", 1)
            return util.load_class(default_module_path.split("."), default_class_name)

    def _validate_class_paths(self) -> None:
        """
        Check the shape of every lazily resolved class path at construction, so a malformed value still fails here
        rather than at first use. None is resolved lazily here; a subclass that does overrides this.
        """

    def _class_path(self,
                    key: str) -> str:
        """
        Get the class path for the given config key.

        :param key: The config key naming the class.
        :return: The class path.
        """
        return self._get(key)

    def _validate_bs4_parser(self) -> None:
        bs4_parser = self._get("bs4_parser")
        try:
            BeautifulSoup("", str(bs4_parser))
        except FeatureNotFound:
            logger.warning(
                f"Configured bs4_parser '{bs4_parser}' is unavailable; "
                f"using the default 'html.parser'. To use it, install the parser "
                f"(e.g. `pip install {self.PACKAGE_NAME}[lxml]`)."
            )
            source = self._environment if "bs4_parser" in self._environment else self._data
            source["bs4_parser"] = "html.parser"

    def _instantiate_constants(self) -> Any:
        constants_cls = self._load_configured_class("constants_class")
        # Pass ``self`` only when the constants class accepts a config arg, to keep backward
        # compatibility with existing zero-arg ``constants_class`` subclasses.
        init_params = inspect.signature(constants_cls.__init__).parameters
        if len(init_params) > 1:
            return constants_cls(self)
        return constants_cls()

    def set_domain(self,
                   domain: str) -> None:
        """
        Set the active Amazon domain and rebuild :attr:`~amazonauth.conf.AmazonAuthConfig.constants`
        so URL-derived attributes and region-sensitive headers reflect the change.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL.
        """
        self._data["domain"] = domain
        self.constants = self._instantiate_constants()

    @property
    def site(self) -> str:
        """The active Amazon site, the host of the ``domain`` without ``www.`` (e.g. ``amazon.de``)."""
        return (urlparse(self.constants.BASE_URL).hostname or "").removeprefix("www.")

    @property
    def cookie_jar_path(self) -> str:
        """
        The path the session for the active ``domain`` is persisted to, since each Amazon site has its own sign-in.
        With the default ``cookie_jar_path``, the ``amazon.com`` session is kept there (``cookies.json``), and every
        other site's beside it, named for the site (e.g. ``cookies.amazon.de.json``). Any other ``cookie_jar_path``
        is used as-is, whatever the site.
        """
        cookie_jar_path = self._get("cookie_jar_path")
        if cookie_jar_path != self._default_cookie_jar_path() or self.site == DEFAULT_COOKIE_JAR_SITE:
            return cookie_jar_path

        root, extension = os.path.splitext(cookie_jar_path)
        return f"{root}.{self.site}{extension}"

    @cookie_jar_path.setter
    def cookie_jar_path(self,
                        value: str) -> None:
        self._data["cookie_jar_path"] = value

    @property
    def shared_cookie_jar_path(self) -> Optional[str]:
        """
        The default ``cookie_jar_path``, which every site's session was persisted to before each site had its own,
        when the active ``domain`` now has a jar of its own (see :attr:`cookie_jar_path`), otherwise ``None``.
        """
        shared_cookie_jar_path = self._get("cookie_jar_path")
        if self.cookie_jar_path == shared_cookie_jar_path:
            return None

        return shared_cookie_jar_path

    def __getattr__(self,
                    key: str) -> Any:
        return self._get(key)

    def __contains__(self,
                     key: str) -> bool:
        return key in self._environment or key in self._data

    def __getstate__(self) -> Dict[str, Any]:
        return {"config_path": self.config_path, "_data": self._data, "_environment": self._environment,
                "_assigned_classes": self._assigned_classes}

    def __setstate__(self,
                     state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self.__dict__.setdefault("_environment", {})
        self._resolved_classes = {}
        self._unavailable_class_paths = set()
        self._load_classes()

    def update_config(self,
                      key: str,
                      value: Union[str, int, float, bool, None],
                      save: bool = True) -> None:
        """
        Update the given key/value pair in the config object. By default, this update will also be persisted to the
        config file. If only the object should be updated without persisting, pass ``save=False``.

        :param key: The key to be updated.
        :param value: The new value.
        :param save: ``True`` if the config should be persisted.
        """
        previous_data = dict(self._data)
        self._data[key] = value
        try:
            self._validate_bs4_parser()
            self._validate_class_paths()
            if key in ("constants_class", "selectors_class"):
                module_path, class_name = self._class_path(key).rsplit(".", 1)
                util.load_class(module_path.split("."), class_name)
            self._load_classes()
        except (AmazonAuthError, AttributeError, ImportError):
            self._data = previous_data
            self._load_classes()
            raise

        self._assigned_classes.pop(key, None)
        self._resolved_classes = {}

        if save:
            self.save()

    def save(self) -> None:
        """
        Persist the current state of this config object to the config file.
        """
        with config_file_lock:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w") as config_file:
                logger.debug(f"Saving config to {self.config_path} ...")

                yaml.dump(self._data, config_file)
