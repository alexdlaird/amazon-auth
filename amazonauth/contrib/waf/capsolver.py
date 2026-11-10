__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict, List, Optional

from amazonauth.contrib.waf.base import AwsWafForm
from amazonauth.exception import AmazonAuthError, AmazonAuthWafSolverError


class CapSolverWafForm(AwsWafForm):
    """
    Passes AWS WAF JavaScript challenges to `CapSolver <https://capsolver.com>`_.

    Its API key is ``CAPSOLVER_API_KEY`` (see :attr:`~amazonauth.contrib.waf.base.AwsWafForm.api_key`).
    Requires the ``capsolver`` Python package: ``pip install amazon-auth[capsolver]``.
    """

    API_KEY_ENV_VAR = "CAPSOLVER_API_KEY"
    PROVIDER_NAME = "CapSolver"

    def solve_token(self,
                    url: str,
                    goku: Dict[str, Any],
                    challenge_script: str) -> str:
        """
        Solve the AWS WAF challenge with CapSolver and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :param goku: The parsed ``window.gokuProps`` payload.
        :param challenge_script: The ``src`` of the AWS WAF ``challenge.js`` script tag.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonAuthError: if the ``capsolver`` package is not installed.
        :raises AmazonAuthWafSolverError: if CapSolver fails, or its response does not contain the expected
            ``cookie`` field.
        """
        try:
            import capsolver
        except ImportError as e:
            raise AmazonAuthError(
                "CapSolverWafForm requires the [capsolver] extra. "
                f"Install it with: `pip install {self.config.PACKAGE_NAME}[capsolver]`"
            ) from e

        capsolver.api_key = self.api_key

        try:
            solution = capsolver.solve({
                "type": "AntiAwsWafTaskProxyLess",
                "websiteURL": url,
                "awsKey": goku["key"],
                "awsIv": goku["iv"],
                "awsContext": goku["context"],
                "awsChallengeJS": challenge_script,
            })
        except Exception as e:
            raise AmazonAuthWafSolverError(
                f"CapSolver could not solve the AWS WAF challenge: {e}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": str(e)}
            ) from e

        try:
            return solution["cookie"]
        except (KeyError, TypeError) as e:
            raise AmazonAuthWafSolverError(
                f"Unexpected CapSolver response (missing \"cookie\"): {solution!r}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": repr(solution)}
            ) from e

    def solve_visual_captcha(self,
                             url: str,
                             image_data: List[str],
                             question: str) -> Optional[List[int]]:
        """
        Solve a visual grid Puzzle with CapSolver and return the indices of the correct grid cells.

        :param url: The URL of the page containing the Puzzle.
        :param image_data: The Puzzle's grid tiles, as base64-encoded images.
        :param question: The object to identify (e.g. ``"the buckets"``).
        :return: A list of zero-based grid cell indices to select.
        :raises AmazonAuthError: if the ``capsolver`` package is not installed.
        :raises AmazonAuthWafSolverError: if CapSolver fails, or its response does not contain the expected
            fields.
        """
        try:
            import capsolver
        except ImportError as e:
            raise AmazonAuthError(
                "CapSolverWafForm requires the [capsolver] extra. "
                f"Install it with: `pip install {self.config.PACKAGE_NAME}[capsolver]`"
            ) from e

        capsolver.api_key = self.api_key

        images_b64 = []
        for img in image_data:
            images_b64.append(img.split(",", 1)[1] if "," in img else img)

        question_id = f"aws:grid:{question.replace('the ', '').rstrip('s')}"

        try:
            solution = capsolver.solve({
                "type": "AwsWafClassification",
                "websiteURL": url,
                "images": images_b64,
                "question": question_id,
            })
        except Exception as e:
            raise AmazonAuthWafSolverError(
                f"CapSolver could not solve the AWS WAF Puzzle: {e}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": str(e)}
            ) from e

        try:
            return solution["objects"]
        except (KeyError, TypeError) as e:
            raise AmazonAuthWafSolverError(
                f"Unexpected CapSolver Puzzle response (missing \"objects\"): {solution!r}",
                meta={"provider": self.PROVIDER_NAME, "provider_error": repr(solution)}
            ) from e
