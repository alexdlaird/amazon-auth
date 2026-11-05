__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
import platform
import sys
from typing import Any, List, Optional

import click
from click.core import Context

from amazonauth import __version__
from amazonauth.conf import AmazonAuthConfig
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


@click.group()
@click.option("--username", help="An Amazon username.")
@click.option("--password", help="An Amazon password.")
@click.option("--debug", is_flag=True, default=False,
              help="Enable debugging and send output to "
                   "command line.")
@click.option("--config-path",
              help="The config path.")
@click.option("--max-auth-attempts",
              help="The max auth loop attempts to make (successes and failures), passing this overrides config value.")
@click.option("--output-dir",
              help="The directory where any output files should be produced, passing this overrides config value.")
@click.option("--domain",
              help="The Amazon domain to target (e.g. amazon.com, amazon.co.uk, amazon.com.au). "
                   "Defaults to amazon.com.")
@click.pass_context
def amazon_auth_cli(ctx: Context,
                    **kwargs: Any) -> None:
    """
    amazon-auth signs in to Amazon's consumer website and persists the session, so it can be reused from the
    CLI or Python.

    Documentation can be found at https://amazon-auth.readthedocs.io.
    """
    ctx.ensure_object(dict)
    for key, value in kwargs.items():
        if value:
            ctx.obj[key] = value

    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

    data = {}
    if kwargs.get("output_dir"):
        data["output_dir"] = kwargs["output_dir"]
    if kwargs.get("max_auth_attempts"):
        data["max_auth_attempts"] = kwargs["max_auth_attempts"]
    if kwargs.get("domain"):
        data["domain"] = kwargs["domain"]
    ctx.obj["conf_data"] = data

    if ctx.invoked_subcommand == "version":
        return

    try:
        ctx.obj["conf"] = AmazonAuthConfig(config_path=kwargs.get("config_path"),
                                           data=data)
    except AmazonAuthError as e:
        ctx.fail(str(e))

    username = kwargs.get("username")
    password = kwargs.get("password")

    amazon_session = AmazonSession(username,
                                   password,
                                   debug=kwargs["debug"],
                                   io=IOClick(),
                                   config=ctx.obj["conf"])

    ctx.obj["amazon_session"] = amazon_session


@amazon_auth_cli.command(short_help="Check if a persisted session exists.")
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


@amazon_auth_cli.command()
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


@amazon_auth_cli.command()
@click.pass_context
def logout(ctx: Context) -> None:
    """
    Log out of existing Amazon sessions and clear cookies.
    """
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.logout()

    click.echo("Info: Successfully logged out of Amazon.\n")


@amazon_auth_cli.command()
@click.pass_context
def version(ctx: Context) -> None:
    """
    Show the banner and package version.
    """
    click.echo(f"amazon-auth/{__version__} Python/{platform.python_version()}")
    ctx.exit(0)


if __name__ == "__main__":
    amazon_auth_cli(obj={})
