__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import pickle
from unittest.mock import patch

import yaml

from amazonauth import conf
from amazonauth.conf import AmazonAuthConfig
from amazonauth.exception import AmazonAuthError
from tests.unittestcase import UnitTestCase


class TestConf(UnitTestCase):
    def test_provision_config(self):
        # WHEN
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml")
        self.assertFalse(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        self.assertFalse(os.path.exists(self.test_cookie_jar_path))

        # GIVEN
        config = AmazonAuthConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path
        })

        # THEN constructing the config touches nothing on disk
        self.assertEqual(5, config.auth_reattempt_wait)
        self.assertEqual(config_path, config.config_path)
        self.assertFalse(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        self.assertFalse(os.path.exists(os.path.dirname(self.test_cookie_jar_path)))
        self.assertEqual(10, config.max_cookie_attempts)
        self.assertEqual(0.5, config.cookie_reattempt_wait)
        self.assertEqual(10, config.max_auth_attempts)
        self.assertEqual(1, config.max_auth_retries)
        self.assertEqual(self.test_output_dir, config.output_dir)
        self.assertEqual(self.test_cookie_jar_path, config.cookie_jar_path)
        self.assertEqual("html.parser", config.bs4_parser)
        self.assertIsNone(config.request_timeout)

        # GIVEN
        config.save()

        # THEN save() provisions the config dir itself
        thread_pool_size = os.cpu_count() * 4
        self.assertTrue(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertTrue(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        with open(config.config_path, "r") as f:
            self.assertEqual("""auth_forms_classes: []
auth_reattempt_wait: 5
browser_timeout: 30
bs4_parser: html.parser
connection_pool_size: {connection_pool_size}
constants_class: amazonauth.constants.AuthConstants
cookie_jar_path: {cookie_jar_path}
cookie_reattempt_wait: 0.5
max_auth_attempts: 10
max_auth_retries: 1
max_cookie_attempts: 10
output_dir: {output_dir}
request_timeout: null
selectors_class: amazonauth.selectors.AuthSelectors
"""
                             .format(connection_pool_size=thread_pool_size * 2,
                                     cookie_jar_path=self.test_cookie_jar_path,
                                     output_dir=self.test_output_dir), f.read())

    def test_override_default(self):
        # GIVEN
        # Default is 10
        config = AmazonAuthConfig(data={
            "max_auth_attempts": 11,
            "request_timeout": 15
        })

        self.assertEqual(11, config.max_auth_attempts)
        self.assertEqual(15, config.request_timeout)

    def test_load_from_file(self):
        # GIVEN
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config.yml")
        test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config-output")
        test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config-cookies.json")
        os.makedirs(conf.DEFAULT_CONFIG_DIR)
        with open(config_path, "w") as f:
            f.write("""cookie_jar_path: {cookie_jar_path}
max_auth_attempts: 11
output_dir: {output_dir}
some_custom_config: {custom_config}
"""
                    .format(cookie_jar_path=test_cookie_jar_path,
                            output_dir=test_output_dir,
                            custom_config="my-custom-config"))

        # WHEN
        config = AmazonAuthConfig(config_path=config_path)

        self.assertEqual(config_path, config.config_path)
        self.assertEqual(11, config.max_auth_attempts)
        self.assertEqual(test_output_dir, config.output_dir)
        self.assertEqual(test_cookie_jar_path, config.cookie_jar_path)
        self.assertEqual("my-custom-config", config.some_custom_config)

    def test_unavailable_bs4_parser_falls_back_to_html_parser(self):
        # GIVEN / WHEN
        with self.assertLogs("amazonauth.conf", level="DEBUG") as logs:
            config = AmazonAuthConfig(data={
                "bs4_parser": "this-parser-does-not-exist"
            })

        # THEN
        self.assertEqual("html.parser", config.bs4_parser)
        self.assertTrue(any("this-parser-does-not-exist" in m for m in logs.output))

    def test_update_config(self):
        # GIVEN
        config = AmazonAuthConfig(data={
            "max_auth_attempts": 11
        })

        self.assertEqual(11, config.max_auth_attempts)

        # WHEN
        config.update_config("max_auth_attempts", 7)
        config.update_config("username", "test-username")
        config.update_config("otp_secret_key", "test-otp-secret-key")

        # THEN
        self.assertEqual(7, config.max_auth_attempts)
        self.assertEqual("test-username", config.username)
        self.assertEqual("test-otp-secret-key", config.otp_secret_key)
        with open(config.config_path, "r") as f:
            persisted_config = yaml.safe_load(f)
            self.assertEqual(7, persisted_config["max_auth_attempts"])
            self.assertEqual("test-username", persisted_config["username"])
            self.assertEqual("test-otp-secret-key", persisted_config["otp_secret_key"])

    def given_config_file(self, contents):
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml")
        os.makedirs(conf.DEFAULT_CONFIG_DIR, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(contents)
        return config_path

    def test_environment_variable_sets_config_value_as_yaml(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20", "AMAZON_AUTH_FORMS_CLASSES": "[a.b.C]"}):
            config = AmazonAuthConfig()

        # THEN
        self.assertEqual(20, config.max_auth_attempts)
        self.assertEqual(["a.b.C"], config.auth_forms_classes)

    def test_environment_variable_without_default_is_used_verbatim(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_PASSWORD": "0123", "AMAZON_BROWSER": "yes"}):
            config = AmazonAuthConfig()

        # THEN
        self.assertEqual("0123", config.password)
        self.assertEqual("yes", config.browser)

    def test_environment_variable_wins_over_data_and_config_file(self):
        # GIVEN
        config_path = self.given_config_file("max_auth_attempts: 11\noutput_dir: /from/file\n")

        # WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonAuthConfig(config_path=config_path, data={"max_auth_attempts": 15})

        # THEN
        self.assertEqual(20, config.max_auth_attempts)
        self.assertEqual("/from/file", config.output_dir)
        self.assertIn("max_auth_attempts", config)

    def test_environment_variable_wins_over_update_config(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonAuthConfig()

        # WHEN
        config.update_config("max_auth_attempts", 7, save=False)

        # THEN
        self.assertEqual(20, config.max_auth_attempts)

    def test_empty_environment_variable_is_ignored(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": ""}):
            config = AmazonAuthConfig()

        # THEN
        self.assertEqual(10, config.max_auth_attempts)

    def test_invalid_yaml_environment_variable_raises(self):
        # WHEN
        with patch.dict(os.environ, {"AMAZON_AUTH_FORMS_CLASSES": "[unclosed"}):
            with self.assertRaises(AmazonAuthError) as cm:
                AmazonAuthConfig()

        # THEN
        self.assertIn("Environment variable AMAZON_AUTH_FORMS_CLASSES is not valid YAML", str(cm.exception))

    def test_environment_variables_are_never_persisted(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_PASSWORD": "secret", "AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonAuthConfig(data={"output_dir": self.test_output_dir})

        # WHEN
        config.update_config("max_auth_attempts", 7)

        # THEN
        with open(config.config_path, "r") as f:
            persisted_config = yaml.safe_load(f)
        self.assertNotIn("password", persisted_config)
        self.assertEqual(7, persisted_config["max_auth_attempts"])

    def test_environment_values_survive_pickling(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonAuthConfig()

        # WHEN
        unpickled_config = pickle.loads(pickle.dumps(config))

        # THEN
        self.assertEqual(20, unpickled_config.max_auth_attempts)
        self.assertEqual(20, unpickled_config.environment_value("max_auth_attempts"))

    def test_environment_variable_sets_domain(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_DOMAIN": "amazon.co.uk"}):
            config = AmazonAuthConfig()

        # THEN
        self.assertEqual("https://www.amazon.co.uk", config.constants.BASE_URL)

    def test_cookie_jar_path_per_site(self):
        # GIVEN
        shared_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")

        # WHEN
        config = AmazonAuthConfig(data={"domain": "amazon.de"})

        # THEN amazon.com keeps the default jar, and every other site gets its own beside it
        self.assertEqual("amazon.de", config.site)
        self.assertEqual(os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.amazon.de.json"), config.cookie_jar_path)
        self.assertEqual(shared_cookie_jar_path, config.shared_cookie_jar_path)

        # WHEN
        config.set_domain("https://www.amazon.com")

        # THEN
        self.assertEqual("amazon.com", config.site)
        self.assertEqual(shared_cookie_jar_path, config.cookie_jar_path)
        self.assertIsNone(config.shared_cookie_jar_path)

    def test_cookie_jar_path_per_site_after_save(self):
        # GIVEN the default cookie_jar_path is persisted, as save() persists every default
        AmazonAuthConfig(data={"domain": "amazon.co.uk"}).save()

        # WHEN
        config = AmazonAuthConfig()

        # THEN
        self.assertEqual(os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.amazon.co.uk.json"), config.cookie_jar_path)

    def test_explicit_cookie_jar_path_wins_for_every_site(self):
        # GIVEN
        explicit_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "my-cookies.json")

        # WHEN
        config = AmazonAuthConfig(data={"domain": "amazon.de", "cookie_jar_path": explicit_cookie_jar_path})

        # THEN
        self.assertEqual(explicit_cookie_jar_path, config.cookie_jar_path)
        self.assertIsNone(config.shared_cookie_jar_path)

        # WHEN
        with patch.dict(os.environ, {"AMAZON_COOKIE_JAR_PATH": "/some/env-cookies.json"}):
            config = AmazonAuthConfig(data={"domain": "amazon.de"})

        # THEN
        self.assertEqual("/some/env-cookies.json", config.cookie_jar_path)

    def test_cookie_jar_path_setter(self):
        # GIVEN
        config = AmazonAuthConfig(data={"domain": "amazon.de"})

        # WHEN
        config.cookie_jar_path = "/some/cookies.json"

        # THEN
        self.assertEqual("/some/cookies.json", config.cookie_jar_path)
