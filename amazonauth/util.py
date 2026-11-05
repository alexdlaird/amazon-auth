__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import logging
import os
import re
import sys
from typing import List, Union, Optional, Callable, Any

from bs4 import Tag, BeautifulSoup
from requests import Response

from amazonauth.selectors import Selector

logger = logging.getLogger(__name__)


class AmazonSessionResponse:
    """
    A wrapper for the :class:`requests.Response` object, which also contains the parsed HTML.
    """

    def __init__(self, response: Response, bs4_parser: str, binary: bool = False) -> None:
        #: The request's response object.
        self.response: Response = response
        #: The parsed HTML from the response, which is empty if the response is ``binary``.
        self.parsed: Tag = BeautifulSoup("" if binary else self.response.text, bs4_parser)


def _selector_text_matches(tag: Tag, selector: Selector) -> bool:
    if selector.text is not None:
        return tag.text.strip() == selector.text
    if selector.text_contains is not None:
        return selector.text_contains.lower() in tag.text.lower()
    return False


def select(parsed: Tag, selector: Union[List[Union[str, Selector]], Union[str, Selector]]) -> List[Tag]:
    """
    This is a helper function that extends BeautifulSoup's `select() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated list of ``Tag``'s, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selected tag.
    """
    if isinstance(selector, str) or isinstance(selector, Selector):
        selector = [selector]

    for s in selector:
        tag: list = []

        if isinstance(s, Selector):
            for t in parsed.select(s.css_selector):
                if t and _selector_text_matches(t, s):
                    tag.append(t)
        elif isinstance(s, str):
            tag = parsed.select(s)
        else:
            raise TypeError(f"Invalid selector type: {type(s)}")

        if tag:
            return tag

    return []


def select_one(parsed: Tag,
               selector: Union[List[Union[str, Selector]], Union[str, Selector]]) -> Optional[Tag]:
    """
    This is a helper function that extends BeautifulSoup's `select_one() <https://www.crummy.com/software/
    BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_ method to allow for multiple selectors.
    The ``selector`` can be either a ``str`` or a ``list``. If a ``list`` is given, each selector in the list will be
    tried until one is found to return a populated ``Tag``, and that value will be returned.

    :param parsed: The ``Tag`` from which to attempt selection.
    :param selector: The CSS selector(s) for the field.
    :return: The selection tag.
    """
    if isinstance(selector, str) or isinstance(selector, Selector):
        selector = [selector]

    for s in selector:
        tag: Optional[Tag] = None

        if isinstance(s, Selector):
            for t in parsed.select(s.css_selector):
                if t and _selector_text_matches(t, s):
                    tag = t
                    break
        elif isinstance(s, str):
            tag = parsed.select_one(s)
        else:
            raise TypeError(f"Invalid selector type: {type(s)}")

        if tag:
            return tag

    return None


def load_class(package: List[str], clazz: str) -> Union[Callable, Any]:
    """
    Import the given class from the given package, and return it.

    :param package: The package.
    :param clazz: The class to import.
    :return: The return class.
    """
    constants_mod = importlib.import_module(".".join(package))
    return getattr(constants_mod, clazz)


def has_display() -> bool:
    """
    Check whether a browser window can be opened here, as signing in with a browser window needs. On Linux, that
    needs a display (``DISPLAY`` or ``WAYLAND_DISPLAY``), which a server or a container usually doesn't have. Other
    platforms always have one.

    :return: Whether there's a display.
    """
    return not sys.platform.startswith("linux") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def cleanup_html_text(text: str) -> str:
    """
    Cleanup excessive whitespace within text that comes from an HTML block.

    :param text: The text to clean up.
    :return: The cleaned up text.
    """
    # First get rid of leading and trailing whitespace
    text = text.strip()
    # Reduce duplicated line returns, then replace line returns with periods
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = text.replace("\n", ". ")
    # Remove remaining duplicated whitespace of any kind
    text = re.sub(r"\s\s+", " ", text)
    # Remove duplicate periods at end of text.
    text = re.sub("\\.+($|\\s)", r".\1", text)
    if not text.endswith("."):
        text += "."
    return text
