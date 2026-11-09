__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import time
from unittest import mock

import pytest

from amazonauth.conf import AmazonAuthConfig
from amazonauth.exception import AmazonAuthError, AmazonAuthSignInError
from amazonauth.session import AmazonSession
from tests.integrationtestcase import IntegrationTestCase


skip_unless_lockout_risk_allowed = pytest.mark.skipif(
    not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH_LOCKOUT_RISK", "False") == "True",
    reason="These tests sign in extra times or submit bad credentials, which raises the risk of Captcha challenges "
           "or locking the account, so they stay off CI. Set AMAZON_INTEGRATION_TEST_AUTH_LOCKOUT_RISK=True "
           "explicitly to run.")
skip_unless_auth = pytest.mark.skipif(
    not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH", "False") == "True",
    reason="Running auth tests too frequently may lock the account. Set AMAZON_INTEGRATION_TEST_AUTH=True "
           "explicitly to run.")


@skip_unless_auth
class TestIntegrationAuth(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account to validate authentication.
    """

    @classmethod
    def setUpClass(cls):
        super().set_up_class_conf()

    def setUp(self):
        if os.path.exists(self.test_config.cookie_jar_path):
            os.remove(self.test_config.cookie_jar_path)

    def tearDown(self):
        print(f"... sleeping {self.teardown_sleep_time} seconds to slow down between auth tests ...")
        time.sleep(self.teardown_sleep_time)

    def given_config_reading_environment(self):
        return AmazonAuthConfig(data={
            "output_dir": self.test_config.output_dir,
            "cookie_jar_path": self.test_config.cookie_jar_path
        })

    def test_logout(self):
        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_session.login()
        old_session = amazon_session.session
        time.sleep(1)

        # WHEN
        amazon_session.logout()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        self.assertFalse(amazon_session.auth_cookies_stored())
        self.assertNotEqual(old_session, amazon_session.session)

    def test_login_no_account(self):
        with mock.patch.dict(os.environ, {"AMAZON_USERNAME": "08511698-9ff5-fake@gmail.com"}):
            # GIVEN
            amazon_session = AmazonSession(debug=self.debug,
                                           config=self.given_config_reading_environment())

            # WHEN
            with self.assertRaises(AmazonAuthSignInError) as cm:
                amazon_session.login()

            # THEN
            self.assertFalse(amazon_session.is_authenticated)
            self.assertIn("Looks like you're new to Amazon", str(cm.exception))

    @skip_unless_lockout_risk_allowed
    def test_login_wrong_password(self):
        with mock.patch.dict(os.environ, {"AMAZON_PASSWORD": "invalid-password"}):
            # GIVEN
            amazon_session = AmazonSession(debug=self.debug,
                                           config=self.given_config_reading_environment())

            # WHEN
            with self.assertRaises(AmazonAuthError) as cm:
                amazon_session.login()

            # THEN
            self.assertFalse(amazon_session.is_authenticated)
            if isinstance(cm.exception, AmazonAuthSignInError):
                self.assertIn("Error from Amazon:", str(cm.exception))
                self.assertIn("password", str(cm.exception))
            else:
                self.assertIn("CaptchaForm", str(cm.exception))
