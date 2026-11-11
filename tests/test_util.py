__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from unittest.mock import patch

from bs4 import BeautifulSoup

from amazonauth.selectors import Selector
from amazonauth.util import cleanup_html_text, has_display, select, select_one
from tests.unittestcase import UnitTestCase


class TestUtil(UnitTestCase):
    def test_cleanup_html_text(self):
        self.assertEqual(cleanup_html_text("""This is a paragraph.
        
        
        So much space. More space.
        This sentence will have period added
        So will this one with two spaces
        
        And then some more.
        
        And that's all"""  # noqa: W293
                                           ),
                         "This is a paragraph. So much space. More space. This sentence will have period "
                         "added. So will this one with two spaces. And then some more. And that's all.")
        self.assertEqual(cleanup_html_text(""" There was a problem
        
        The One Time Password (OTP) you entered is not valid.
        
        Please try again
        
        """  # noqa: W293
                                           ),
                         "There was a problem. The One Time Password (OTP) you entered is not valid. "
                         "Please try again.")
        self.assertEqual(cleanup_html_text("""
        
        This has leading newlines.
        
        They should be removed
        
        """  # noqa: W293
                                           ), "This has leading newlines. They should be removed.")

    def test_select_with_text_selector_returns_matched_tags(self):
        # GIVEN
        parsed = BeautifulSoup("<div><span>Rewards balance</span><span>Other</span>"
                               "<p><b>Rewards balance</b></p><i>Rewards balance</i></div>",
                               self.test_config.bs4_parser)

        # WHEN
        tags = select(parsed, Selector("span, b", text="Rewards balance"))

        # THEN
        self.assertEqual(["span", "b"], [t.name for t in tags])
        self.assertEqual(["Rewards balance", "Rewards balance"], [t.text for t in tags])

    def test_select_with_text_selector_returns_tag_not_children(self):
        # GIVEN
        parsed = BeautifulSoup("<div><span class=\"s\"><b>Rewards balance</b> <i>(updated today)</i></span>"
                               "<span class=\"s\">Other</span></div>",
                               self.test_config.bs4_parser)

        # WHEN
        tags = select(parsed, Selector("span.s", text_contains="Rewards balance"))

        # THEN
        self.assertEqual(1, len(tags))
        self.assertEqual("span", tags[0].name)

    def test_select_one_with_text_selector_returns_first_matched_tag(self):
        # GIVEN
        parsed = BeautifulSoup("<ul><li><span class=\"label\">Total</span><p>$1.00</p></li>"
                               "<li><span class=\"label\">Order Number</span><p>123-1234567-1234567</p></li>"
                               "<li><span class=\"label\">Receipts</span><p>n/a</p></li></ul>",
                               self.test_config.bs4_parser)

        # WHEN
        tag = select_one(parsed, Selector("span.label", text="Order Number"))

        # THEN
        self.assertIsNotNone(tag)
        self.assertEqual("Order Number", tag.text)
        self.assertEqual("123-1234567-1234567", tag.find_next_sibling("p").text)

    def test_select_one_with_text_selector_returns_none_when_no_text_matches(self):
        # GIVEN
        parsed = BeautifulSoup("<ul><li><span class=\"label\">Total</span></li>"
                               "<li><span class=\"label\">Order Number</span></li></ul>",
                               self.test_config.bs4_parser)

        # WHEN
        tag = select_one(parsed, Selector("span.label", text="Subtotal"))

        # THEN
        self.assertIsNone(tag)

    @patch("amazonauth.util.sys.platform", "linux")
    def test_has_display_supplied_environment(self):
        with patch.dict(os.environ, {"DISPLAY": ":1"}):
            self.assertFalse(has_display({}))
            self.assertTrue(has_display({"DISPLAY": ":42"}))
            self.assertTrue(has_display({"WAYLAND_DISPLAY": "wayland-2"}))
            self.assertTrue(has_display())

    @patch.object(sys, "platform", "linux")
    def test_has_display_linux_without_display(self):
        # GIVEN
        with patch.dict(os.environ):
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)

            # WHEN / THEN
            self.assertFalse(has_display())

    @patch.object(sys, "platform", "linux")
    def test_has_display_linux_with_display(self):
        # GIVEN
        for name, value in (("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")):
            with self.subTest(name=name), patch.dict(os.environ, {name: value}):
                os.environ.pop("WAYLAND_DISPLAY" if name == "DISPLAY" else "DISPLAY", None)

                # WHEN / THEN
                self.assertTrue(has_display())

    @patch.object(sys, "platform", "darwin")
    def test_has_display_assumed_off_linux(self):
        # GIVEN
        with patch.dict(os.environ):
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)

            # WHEN / THEN
            self.assertTrue(has_display())
