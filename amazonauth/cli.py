__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import sys
from typing import Any, List, Optional

import click
from click.core import Context

from amazonauth.contrib.browser.playwright import PlaywrightBrowserLauncher, PlaywrightBrowserLogin
from amazonauth.exception import AmazonAuthBrowserNotInstalledError, AmazonAuthError, AmazonAuthSignInError
from amazonauth.session import AmazonSession, IODefault

logger = logging.getLogger("amazonauth")


class IOClick(IODefault):
    def echo(self,
             msg: str,
             fg: Optional[str] = None,
             **kwargs: Any) -> None:
        click.secho(msg, fg=fg)

    def prompt(self,
               msg: str,
               type: Optional[Any] = None,
               **kwargs: Any) -> Any:
        for choice in kwargs.get("choices", []):
            self.echo(choice, **kwargs)

        return click.prompt(f"--> {msg}", type=type)

    @staticmethod
    def prompt_for_choice(msg: str,
                          choices: List[str]) -> str:
        for number, choice in enumerate(choices, start=1):
            click.echo(f"{number}: {choice}")
        click.echo(f"--> {msg} [1]: ", nl=False)

        while True:
            key = click.getchar()
            if key in ("\r", "\n"):
                number = 1
            elif key.isdigit() and 1 <= int(key) <= len(choices):
                number = int(key)
            else:
                continue

            click.echo(number)
            return choices[number - 1]

    @staticmethod
    def echo_session_expired() -> None:
        click.echo("... Amazon redirected to login, so it wants the persisted session's sign-in confirmed. Call the "
                   "`login` command to sign in again, or `login --browser` to log in on Amazon's own page.\n")


class CliAuth:
    def __init__(self,
                 amazon_session: AmazonSession) -> None:
        self.amazon_session: AmazonSession = amazon_session

    def authenticate(self,
                     retries: int = 0) -> None:
        amazon_session = self.amazon_session
        try:
            if amazon_session.auth_cookies_stored():
                if amazon_session.username or amazon_session.password:
                    click.echo(
                        "Info: The given username and password are being ignored because a previous session still "
                        "exists. To reauthenticate, call the `login` command.\n")
            else:
                if not amazon_session.username:
                    amazon_session.username = click.prompt("Username")
                if not amazon_session.password:
                    amazon_session.password = click.prompt("Password", hide_input=True)
                    click.echo("")

            amazon_session.login()
        except AmazonAuthSignInError as e:
            if retries < amazon_session.config.max_auth_retries:
                if amazon_session.username:
                    click.secho(str(f"{e}\n"), fg="red")
                    click.echo(
                        f"Info: Authenticating '{amazon_session.username}' failed. If using 2FA, wait a minute "
                        "before retrying with a new OTP.\n")

                amazon_session.password = None

                self.authenticate(retries=retries + 1)
            else:
                raise e

    def authenticate_with_browser(self) -> None:
        browser_login = PlaywrightBrowserLogin(self.amazon_session)
        try:
            browser_login.login()
        except AmazonAuthBrowserNotInstalledError as e:
            if not sys.stdin.isatty():
                raise

            browser_types = (e.meta or {})["browser_types"]
            if len(browser_types) == 1:
                click.echo(f"Info: {browser_types[0]} isn't installed.\n")
                if not click.confirm(f"--> Download {browser_types[0]} now?", default=True):
                    raise
                browser_type = browser_types[0]
            else:
                click.echo("Info: No default browser was found, so one to sign in with needs to be downloaded.\n")
                browser_type = IOClick.prompt_for_choice("Choose a browser to download", browser_types)

            browser_selected = PlaywrightBrowserLauncher(self.amazon_session.config).install(browser_type)
            click.echo("")
            if browser_selected:
                click.echo(f"Info: Config \"browser\" updated to \"{browser_type}\".\n")
            browser_login.login()


@click.command(short_help="Check if a persisted session exists.")
@click.pass_context
@click.option("--verify", is_flag=True, default=False,
              help="Also ask Amazon whether it still accepts the persisted session.")
def check_session(ctx: Context, **kwargs: Any) -> None:
    """
    Check if a persisted session exists, meaning commands can be called without needing to provide credentials.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        if amazon_session.check_session(verify=kwargs["verify"]):
            if kwargs["verify"]:
                click.echo("Info: A persisted session exists, and Amazon accepts it.\n")
            else:
                click.echo("Info: A persisted session exists.\n")
        elif amazon_session.auth_cookies_stored():
            click.echo("Info: A persisted session exists, but Amazon no longer accepts it.\n")
            IOClick.echo_session_expired()
        else:
            click.echo("Info: No persisted session exists.\n")
    except AmazonAuthError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@click.command()
@click.pass_context
@click.option("--browser", is_flag=True, default=False,
              help="Sign in with a browser window, so your credentials never need to be stored. "
                   "Requires the browser extra.")
def login(ctx: Context, **kwargs: Any) -> None:
    """
    Log in to establish an Amazon session and cookies.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        if amazon_session.auth_cookies_stored():
            click.echo("Info: Logging out of the persisted session first, so this login starts fresh.\n")
            amazon_session.logout()

        if kwargs["browser"]:
            CliAuth(amazon_session).authenticate_with_browser()
        else:
            CliAuth(amazon_session).authenticate()
    except AmazonAuthError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))

    click.echo("Info: Successfully logged in to Amazon, session persisted.\n")


@click.command()
@click.pass_context
def logout(ctx: Context) -> None:
    """
    Log out of existing Amazon sessions and clear cookies.
    """
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.logout()

    click.echo("Info: Successfully logged out of Amazon.\n")
