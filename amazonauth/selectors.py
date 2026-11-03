__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Callable, Dict, Optional, Tuple


class Selector:
    """
    Can be used to extend the definition of a CSS selector, allowing for programmatic inspection
    of the selections results before determining if selector matches.
    """

    def __init__(self,
                 css_selector: str,
                 text: Optional[str] = None,
                 text_contains: Optional[str] = None) -> None:
        #: The CSS selector.
        self.css_selector: str = css_selector
        #: The text within the tag that must match exactly (after stripping).
        self.text: Optional[str] = text
        #: A substring within the tag's text that must be present (case-insensitive). Evaluated only when
        #: :attr:`text` is not set.
        self.text_contains: Optional[str] = text_contains


class SelectorsFromText:
    """
    Builds a selector, or a list of selectors, from page text attributes of the :class:`AuthSelectors` class it's set
    on, so a subclass that changes the text gets selectors that match it. Selectors built from the same text are
    shared.

    .. code-block:: python

        EXAMPLE_SELECTOR = SelectorsFromText(lambda example_text: [
            Selector("h4.a-alert-heading", text_contains=example_text)
        ], "EXAMPLE_TEXT")
    """

    def __init__(self,
                 build: Callable[..., Any],
                 *attribute_names: str) -> None:
        #: Builds the selector(s), given the values of :attr:`attribute_names`.
        self.build: Callable[..., Any] = build
        #: The names of the :class:`AuthSelectors` attributes the selector(s) are built from.
        self.attribute_names: Tuple[str, ...] = attribute_names
        self._built: Dict[Tuple[Any, ...], Any] = {}

    def __get__(self,
                instance: Optional["AuthSelectors"],
                owner: type) -> Any:
        values = tuple(getattr(owner, name) for name in self.attribute_names)
        if values not in self._built:
            self._built[values] = self.build(*values)

        return self._built[values]


class AuthSelectors:
    """
    A class containing the CSS selectors for Amazon's sign-in pages. Extend and override with ``selectors_class``
    in the config.
    """

    ##########################################################################
    # CSS selectors for Pages
    ##########################################################################

    BAD_INDEX_SELECTOR = "html.a-tablet"

    ##########################################################################
    # CSS selectors for AuthForms
    ##########################################################################

    ACIC_CHALLENGE_SELECTOR = "#aa-challenge-page-captcha-container"
    ACIC_VISUAL_CAPTCHA_MODAL_SELECTOR = ".amzn-captcha-modal"
    ACIC_VISUAL_CAPTCHA_CANVAS_SELECTOR = ".amzn-captcha-modal canvas"
    ACIC_VISUAL_CAPTCHA_QUESTION_SELECTOR = ".amzn-captcha-modal em"
    ACIC_VISUAL_CAPTCHA_VERIFY_SELECTOR = "#amzn-btn-verify-internal"
    AWS_WAF_CHALLENGE_SCRIPT_SELECTOR = 'script[src*="awswaf.com"]'

    SIGN_IN_FORM_SELECTOR = "form[name='signIn']"
    NAV_GREETING_SELECTOR = "#nav-link-accountList-nav-line-1"
    SIGN_IN_EMAIL_INPUT_SELECTOR = "input[name='email']"
    CLAIM_FORM_SELECTOR = ["form[name='signIn'].auth-validate-form", "form#unified-password-form"]
    INTENT_FORM_SELECTOR = ["form#intent-confirmation-form",
                            "form:has(input[name='OTPChallengeOptions'])"]
    INTENT_MESSAGE_SELECTOR = ["div#intent-confirmation-container",
                               "form:has(input[name='OTPChallengeOptions']) > h2"]
    MFA_DEVICE_SELECT_FORM_SELECTOR = "form#auth-select-device-form"
    PASSKEY_FORM_SELECTOR = "form#unified-passkey-form"
    PASSKEY_PASSWORD_CHALLENGE_LINK_SELECTOR = "a[href*='selectedChallengeType=password']"
    MFA_DEVICE_SELECT_INPUT_SELECTOR = "input[name='otpDeviceContext']"
    MFA_DEVICE_SELECT_INPUT_SELECTOR_VALUE = "value"
    MFA_DEVICE_SELECT_LABEL_SELECTOR = "span.a-label.a-radio-label"
    MFA_FORM_SELECTOR = ["form#auth-mfa-form", "form#unified-otp-form"]
    CAPTCHA_1_FORM_SELECTOR = "form.cvf-widget-form-captcha"
    CAPTCHA_2_FORM_SELECTOR = ["form:has(input[id^='captchacharacters'])", "form[action$='validateCaptcha']"]
    CAPTCHA_OTP_FORM_SELECTOR = "form#verification-code-form"
    DEFAULT_ERROR_TAG_SELECTOR = "div#auth-error-message-box:not(.aok-hidden *)"
    CAPTCHA_1_ERROR_SELECTOR = "div.cvf-widget-alert"
    CAPTCHA_2_ERROR_SELECTOR = "div.a-alert-info"
