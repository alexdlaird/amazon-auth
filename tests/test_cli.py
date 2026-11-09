__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from unittest.mock import patch

import click
import responses
from click.testing import CliRunner

from amazonauth.cli import IOClick, check_session, login, logout
from amazonauth.conf import AmazonAuthConfig
from amazonauth.exception import AmazonAuthBrowserNotInstalledError
from amazonauth.session import AmazonSession
from tests.unittestcase import UnitTestCase


@click.group()
@click.option("--username")
@click.option("--password")
@click.option("--config-path")
@click.pass_context
def downstream_cli(ctx, username, password, config_path):
    ctx.ensure_object(dict)
    ctx.obj["amazon_session"] = AmazonSession(username, password, io=IOClick(),
                                              config=AmazonAuthConfig(config_path=config_path))


downstream_cli.add_command(check_session)
downstream_cli.add_command(login)
downstream_cli.add_command(logout)


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.test_config.save()

        self.runner = CliRunner()

    @responses.activate
    def test_login_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "login"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertIn("Successfully logged in to Amazon", response.output)

    def given_browser_not_installed(self, mock_browser_login, browser_types):
        mock_browser_login.return_value.login.side_effect = [
            AmazonAuthBrowserNotInstalledError("Not installed.", meta={"browser_types": browser_types}),
            None
        ]

    def invoke_login_with_browser(self, input=None):
        return self.runner.invoke(downstream_cli,
                                  ["--config-path", self.test_config.config_path, "login", "--browser"],
                                  input=input)

    @patch("amazonauth.cli.sys")
    @patch("amazonauth.cli.PlaywrightBrowserLauncher")
    @patch("amazonauth.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_downloads_chosen_browser_and_retries(self, mock_browser_login, mock_launcher,
                                                                     mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])
        mock_launcher.return_value.install.return_value = True

        # WHEN
        response = self.invoke_login_with_browser(input="x2")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("1: chromium\n2: firefox\n3: webkit\n--> Choose a browser to download [1]: 2\n",
                      response.output)
        mock_launcher.return_value.install.assert_called_once_with("firefox")
        self.assertIn("Config \"browser\" updated to \"firefox\"", response.output)
        self.assertEqual(2, mock_browser_login.return_value.login.call_count)

    @patch("amazonauth.cli.sys")
    @patch("amazonauth.cli.PlaywrightBrowserLauncher")
    @patch("amazonauth.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_enter_downloads_default_browser(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])
        mock_launcher.return_value.install.return_value = False

        # WHEN
        response = self.invoke_login_with_browser(input="\r")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("--> Choose a browser to download [1]: 1\n", response.output)
        mock_launcher.return_value.install.assert_called_once_with("chromium")

    @patch("amazonauth.cli.sys")
    @patch("amazonauth.cli.PlaywrightBrowserLauncher")
    @patch("amazonauth.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_confirms_single_browser_type(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["firefox"])
        mock_launcher.return_value.install.return_value = False

        # WHEN
        response = self.invoke_login_with_browser(input="\n")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("Download firefox now? [Y/n]", response.output)
        mock_launcher.return_value.install.assert_called_once_with("firefox")
        self.assertNotIn("Config \"browser\" updated", response.output)

    @patch("amazonauth.cli.sys")
    @patch("amazonauth.cli.PlaywrightBrowserLauncher")
    @patch("amazonauth.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_declined_download_fails(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["firefox"])

        # WHEN
        response = self.invoke_login_with_browser(input="n\n")

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Not installed.", response.output)
        mock_launcher.return_value.install.assert_not_called()

    @patch("amazonauth.cli.PlaywrightBrowserLauncher")
    @patch("amazonauth.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_without_terminal_does_not_prompt(self, mock_browser_login, mock_launcher):
        # GIVEN
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])

        # WHEN
        response = self.invoke_login_with_browser()

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Not installed.", response.output)
        self.assertNotIn("Choose a browser", response.output)
        mock_launcher.return_value.install.assert_not_called()

    @responses.activate
    def test_logout_command(self):
        # GIVEN
        self.given_persisted_session_exists()
        signout_response = self.given_logout_response_success()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "logout"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, signout_response.call_count)
        self.assertIn("Successfully logged out of Amazon", response.output)

    @responses.activate
    def test_check_session_command(self):
        # GIVEN
        self.given_persisted_session_exists()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(0, len(responses.calls))
        self.assertIn("A persisted session exists.", response.output)

    @responses.activate
    def test_check_session_command_no_persisted_session(self):
        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(0, len(responses.calls))
        self.assertIn("No persisted session exists.", response.output)

    @responses.activate
    def test_check_session_command_verify(self):
        # GIVEN
        self.given_persisted_session_exists()
        history_response = self.given_session_check_page_exists()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session",
                                          "--verify"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, history_response.call_count)
        self.assertIn("A persisted session exists, and Amazon accepts it.", response.output)

    @responses.activate
    def test_check_session_command_verify_session_expired(self):
        # GIVEN
        self.given_persisted_session_exists()
        self.given_login_responses_success()
        auth_redirect_response = self.given_authenticated_url_redirects_to_login()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session",
                                          "--verify"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertIn("A persisted session exists, but Amazon no longer accepts it.", response.output)
        self.assertIn("Call the `login` command to sign in again", response.output)

    @responses.activate
    def test_check_session_command_verify_no_persisted_session(self):
        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session",
                                          "--verify"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(0, len(responses.calls))
        self.assertIn("No persisted session exists.", response.output)

    @responses.activate
    def test_check_session_command_verify_response_not_ok(self):
        # GIVEN
        self.given_persisted_session_exists()
        history_response = self.given_session_check_page_exists(status=503)

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session",
                                          "--verify"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, history_response.call_count)
        self.assertIn("returned 503", response.output)

    @responses.activate
    def test_check_session_command_verify_no_response(self):
        # GIVEN
        self.given_persisted_session_exists()

        # WHEN
        response = self.runner.invoke(downstream_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session",
                                          "--verify"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("returned no response", response.output)
