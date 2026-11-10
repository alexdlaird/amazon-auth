__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict

from amazonauth.contrib.waf.base import AwsWafForm
from amazonauth.exception import AmazonAuthError, AmazonAuthWafSolverError


class AntiCaptchaWafForm(AwsWafForm):
    """
    Passes AWS WAF JavaScript challenges to `Anti-Captcha <https://anti-captcha.com>`_.

    Its API key is ``ANTICAPTCHA_API_KEY`` (see :attr:`~amazonauth.contrib.waf.base.AwsWafForm.api_key`).
    Requires the ``anticaptchaofficial`` Python package:
    ``pip install amazon-auth[anticaptcha]``.
    """

    API_KEY_ENV_VAR = "ANTICAPTCHA_API_KEY"
    PROVIDER_NAME = "Anti-Captcha"

    def solve_token(self,
                    url: str,
                    goku: Dict[str, Any],
                    challenge_script: str) -> str:
        """
        Solve the AWS WAF challenge with Anti-Captcha and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :param goku: The parsed ``window.gokuProps`` payload.
        :param challenge_script: The ``src`` of the AWS WAF ``challenge.js`` script tag.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonAuthError: if the ``anticaptchaofficial`` package is
            not installed.
        :raises AmazonAuthWafSolverError: if Anti-Captcha fails, or returns no token.
        """
        try:
            from anticaptchaofficial.amazonproxyless import amazonProxyless
        except ImportError as e:
            raise AmazonAuthError(
                "AntiCaptchaWafForm requires the [anticaptcha] extra. "
                f"Install it with: `pip install {self.config.PACKAGE_NAME}[anticaptcha]`"
            ) from e

        solver = amazonProxyless()
        solver.set_key(self.api_key)
        solver.set_website_url(url)
        solver.set_website_key(goku["key"])
        solver.set_iv(goku["iv"])
        solver.set_context(goku["context"])
        solver.set_challenge_script(challenge_script)

        try:
            token = solver.solve_and_return_solution()
        except Exception as e:
            raise AmazonAuthWafSolverError(
                f"Anti-Captcha could not solve the AWS WAF challenge: {e}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": str(e)}
            ) from e

        if not token:
            error_code = getattr(solver, "error_code", None) or "unknown error"
            raise AmazonAuthWafSolverError(
                f"Anti-Captcha could not solve the AWS WAF challenge: {error_code}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": error_code}
            )
        return token
