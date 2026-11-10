__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict, Optional, Union


class AmazonAuthError(Exception):
    """
    Raised when a general ``amazon-auth`` error has occurred.
    """

    def __init__(self,
                 error: Union[str, BaseException],
                 meta: Optional[Dict[str, Any]] = None) -> None:
        super(AmazonAuthError, self).__init__(error)

        #: Metadata for context around the error was raised.
        self.meta: Optional[Dict[str, Any]] = meta


class AmazonAuthSignInError(AmazonAuthError):
    """
    Raised when an ``amazon-auth`` authentication error has occurred.
    """
    pass


class AmazonAuthRedirectError(AmazonAuthSignInError):
    """
    Raised when an ``amazon-auth`` session that was previously authenticated redirects to login, indicating the
    likely need to reauthenticate.
    """
    pass


class AmazonAuthChallengeUnsolvedError(AmazonAuthError):
    """
    Raised when a sign-in challenge form can't handle the challenge it was given (e.g. a solver without its API key,
    or one that opens a browser window without a display), so the next form registered for the challenge is tried.
    If none can, the error is raised.
    """
    pass


class AmazonAuthWafSolverError(AmazonAuthChallengeUnsolvedError):
    """
    Raised when a third-party WAF solver fails (e.g. its balance ran out, its API key was rejected, or the service
    is down), rather than Amazon rejecting a solved challenge. ``meta["provider"]`` is the solver's name, and
    ``meta["provider_error"]`` is the error it gave.
    """
    pass


class AmazonAuthBrowserNotInstalledError(AmazonAuthError):
    """
    Raised when no browser is installed to sign in with. ``meta["browser_types"]`` lists the Playwright browser types
    that can be installed in its place, the default first.
    """
    pass
