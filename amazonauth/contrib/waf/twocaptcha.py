__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
from typing import Any, Dict

from amazonauth.contrib.waf.base import AwsWafForm
from amazonauth.exception import AmazonAuthError, AmazonAuthWafSolverError


class TwoCaptchaWafForm(AwsWafForm):
    """
    Passes AWS WAF JavaScript challenges to `2Captcha <https://2captcha.com>`_.

    Its API key is ``TWOCAPTCHA_API_KEY`` (see :attr:`~amazonauth.contrib.waf.base.AwsWafForm.api_key`).
    Requires the ``2captcha-python`` Python package:
    ``pip install amazon-auth[2captcha]``.
    """

    API_KEY_ENV_VAR = "TWOCAPTCHA_API_KEY"
    PROVIDER_NAME = "2Captcha"

    def solve_token(self,
                    url: str,
                    goku: Dict[str, Any],
                    challenge_script: str) -> str:
        """
        Solve the AWS WAF challenge with 2Captcha and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :param goku: The parsed ``window.gokuProps`` payload.
        :param challenge_script: The ``src`` of the AWS WAF ``challenge.js`` script tag.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonAuthError: if the ``2captcha-python`` package is not
            installed.
        :raises AmazonAuthWafSolverError: if 2Captcha fails, or its response is malformed or missing the
            expected ``existing_token`` field.
        """
        try:
            from twocaptcha import TwoCaptcha
        except ImportError as e:
            raise AmazonAuthError(
                "TwoCaptchaWafForm requires the [2captcha] extra. "
                f"Install it with: `pip install {self.config.PACKAGE_NAME}[2captcha]`"
            ) from e

        solver = TwoCaptcha(self.api_key)
        try:
            result = solver.amazon_waf(
                sitekey=goku["key"],
                iv=goku["iv"],
                context=goku["context"],
                url=url,
                challenge_script=challenge_script,
            )
        except Exception as e:
            raise AmazonAuthWafSolverError(
                f"2Captcha could not solve the AWS WAF challenge: {e}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": str(e)}
            ) from e

        try:
            return json.loads(result["code"])["existing_token"]
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise AmazonAuthWafSolverError(
                f"Unexpected 2Captcha response (missing \"existing_token\"): {result!r}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": repr(result)}
            ) from e
