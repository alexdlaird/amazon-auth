__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from unittest.mock import patch

from amazonauth.conf import AmazonAuthConfig
from amazonauth.constants import AuthConstants
from amazonauth.exception import AmazonAuthError
from amazonauth.region_data import REGION_SITES
from tests.unittestcase import UnitTestCase


class TestConstants(UnitTestCase):
    _FIREFOX_UA = AuthConstants.BROWSER_HEADERS["firefox"]["User-Agent"]
    _CHROMIUM_UA = AuthConstants.BASE_HEADERS["User-Agent"]

    def test_default_browser_is_chromium(self):
        # GIVEN / WHEN
        constants = AuthConstants()

        # THEN
        self.assertEqual(self._CHROMIUM_UA, constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", constants.BASE_HEADERS)

    def test_firefox_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"browser": "firefox"})

        # THEN
        self.assertEqual(self._FIREFOX_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)

    def test_chromium_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"browser": "chromium"})

        # THEN
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)
        self.assertIn("Sec-Ch-Ua-Mobile", config.constants.BASE_HEADERS)
        self.assertIn("Sec-Ch-Ua-Platform", config.constants.BASE_HEADERS)

    def test_webkit_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"browser": "webkit"})

        # THEN
        self.assertEqual(AuthConstants.BROWSER_HEADERS["webkit"]["User-Agent"],
                         config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Safari/", config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Chrome/", config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)
        self.assertNotIn("Sec-Fetch-User", config.constants.BASE_HEADERS)

    def test_chromium_preset_accept_header(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"browser": "chromium"})

        # THEN
        self.assertIn("image/avif", config.constants.BASE_HEADERS["Accept"])

    def test_firefox_preset_via_env_var(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "firefox"}):
            constants = AuthConstants()

        # THEN
        self.assertEqual(self._FIREFOX_UA, constants.BASE_HEADERS["User-Agent"])

    def test_chromium_preset_via_env_var(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "chromium"}):
            constants = AuthConstants()

        # THEN
        self.assertEqual(self._CHROMIUM_UA, constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", constants.BASE_HEADERS)

    def test_env_var_takes_precedence_over_config_data(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "firefox"}):
            config = AmazonAuthConfig(data={"browser": "chromium"})

        # THEN
        self.assertEqual(self._FIREFOX_UA, config.constants.BASE_HEADERS["User-Agent"])

    def test_installed_chromium_browser_keeps_chromium_headers(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"browser": "chrome"})

        # THEN
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)

    def test_base_headers_have_no_host(self):
        # GIVEN / WHEN
        constants = AuthConstants()
        uk_constants = AmazonAuthConfig(data={"domain": "amazon.co.uk"}).constants

        # THEN
        self.assertNotIn("Host", AuthConstants.BASE_HEADERS)
        self.assertNotIn("Host", constants.BASE_HEADERS)
        self.assertNotIn("Host", uk_constants.BASE_HEADERS)
        self.assertEqual("https://www.amazon.co.uk", uk_constants.BASE_HEADERS["Origin"])

    def test_domain_and_chromium_preset_combined(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={
            "browser": "chromium",
            "domain": "amazon.co.uk",
        })

        # THEN — chromium UA + UK Accept-Language from region override
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("en-GB", config.constants.BASE_HEADERS["Accept-Language"])

    def test_domain_accept_language_overrides_browser_default(self):
        # GIVEN / WHEN — default (chromium) Accept-Language is en-US,en;q=0.9
        config_default = AmazonAuthConfig(data={"domain": "amazon.co.uk"})
        config_ff = AmazonAuthConfig(data={
            "browser": "firefox",
            "domain": "amazon.co.uk",
        })

        # THEN — both get the TLD-specific Accept-Language regardless of browser
        self.assertIn("en-GB", config_default.constants.BASE_HEADERS["Accept-Language"])
        self.assertIn("en-GB", config_ff.constants.BASE_HEADERS["Accept-Language"])

    def test_domain_sets_region_assoc_handle(self):
        for tld, site in REGION_SITES.items():
            if not site.assoc_handle:
                continue
            with self.subTest(tld=tld):
                # GIVEN / WHEN
                config = AmazonAuthConfig(data={"domain": f"amazon.{tld}"})

                # THEN
                self.assertEqual(site.assoc_handle,
                                 config.constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"])
                self.assertIn(f"openid.assoc_handle={site.assoc_handle}",
                              config.constants.BASE_HEADERS["Referer"])

    def test_domain_sets_region_authenticated_cookie(self):
        # GIVEN
        expected_cookies = {
            "amazon.ca": "x-acbca",
            "amazon.co.jp": "x-acbjp",
            "amazon.co.uk": "x-acbuk",
            "amazon.com.au": "x-acbau",
            "amazon.de": "x-acbde",
            "amazon.in": "x-acbin",
            "amazon.it": "x-acbit",
        }

        for domain, expected_cookie in expected_cookies.items():
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonAuthConfig(data={"domain": domain})

                # THEN
                self.assertEqual([expected_cookie], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)

    def test_domain_com_keeps_default_sign_in_and_session_values(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={"domain": "amazon.com"})

        # THEN
        self.assertEqual(AuthConstants.SIGN_IN_QUERY_PARAMS, config.constants.SIGN_IN_QUERY_PARAMS)
        self.assertEqual(AuthConstants.BASE_HEADERS["Referer"], config.constants.BASE_HEADERS["Referer"])
        self.assertEqual(["x-main"], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)

    def test_domain_that_is_not_an_amazon_site_raises(self):
        for domain in ["amazon.example", "amzon.de", "evil.example", "smile.amazon.com", "amazon.de.evil.example",
                       "https://amazon.com.evil.example", "http://www.amazon.de", "https://www.amazon.de/path",
                       "https://www.amazon.de:8443", "https://user:password@www.amazon.de"]:
            with self.subTest(domain=domain):
                # WHEN
                with self.assertRaises(AmazonAuthError) as cm:
                    AmazonAuthConfig(data={"domain": domain})

                # THEN
                self.assertIn(f"The domain \"{domain}\" isn't an Amazon site.", str(cm.exception))
                self.assertIn("amazon.co.uk", str(cm.exception))

    def test_domain_forms_of_an_amazon_site_are_accepted(self):
        for domain, base_url in [("amazon.de", "https://www.amazon.de"), ("www.amazon.de", "https://www.amazon.de"),
                                 ("https://www.amazon.co.uk/", "https://www.amazon.co.uk"),
                                 ("https://amazon.com.au", "https://amazon.com.au")]:
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonAuthConfig(data={"domain": domain})

                # THEN
                self.assertEqual(base_url, config.constants.BASE_URL)

    def test_update_config_with_domain_that_is_not_an_amazon_site_raises_and_keeps_previous(self):
        # GIVEN
        config = AmazonAuthConfig(data={"domain": "amazon.de"})
        config.save()

        # WHEN
        with self.assertRaises(AmazonAuthError):
            config.update_config("domain", "amazon.de.evil.example")

        # THEN
        self.assertEqual("amazon.de", config.domain)
        self.assertEqual("https://www.amazon.de", config.constants.BASE_URL)
        with open(config.config_path, "r") as f:
            self.assertNotIn("evil", f.read())

    def test_domain_sets_region_language_cookie(self):
        for tld, site in REGION_SITES.items():
            if not (site.english_locale and site.language_cookie):
                continue
            with self.subTest(tld=tld):
                # GIVEN / WHEN
                config = AmazonAuthConfig(data={"domain": f"amazon.{tld}"})

                # THEN
                self.assertEqual({site.language_cookie: site.english_locale}, config.constants.REQUEST_COOKIES)

    def test_no_domain_sets_com_language_cookie(self):
        # GIVEN / WHEN
        constants = AuthConstants()

        # THEN
        self.assertEqual({"lc-main": "en_US"}, constants.REQUEST_COOKIES)
        self.assertEqual({}, AuthConstants.REQUEST_COOKIES)

    def test_language_cookie_and_accept_language_request_the_same_locale(self):
        for tld, site in REGION_SITES.items():
            if not (site.english_locale and site.language_cookie):
                continue
            with self.subTest(tld=tld):
                # GIVEN / WHEN
                config = AmazonAuthConfig(data={"domain": f"amazon.{tld}"})
                cookie_locale = next(iter(config.constants.REQUEST_COOKIES.values()))

                # THEN
                self.assertEqual(cookie_locale.replace("_", "-"),
                                 config.constants.BASE_HEADERS["Accept-Language"].split(",")[0],
                                 f"amazon.{tld}'s Accept-Language asks for a different locale than its cookie")

    def test_domain_does_not_override_constants_class_request_cookies(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={
            "constants_class": "tests.test_constants.RequestCookiesOverrideConstants",
            "domain": "amazon.fr",
        })

        # THEN
        self.assertEqual({"lc-acbfr": "fr_FR"}, config.constants.REQUEST_COOKIES)

    def test_domain_does_not_override_constants_class_sign_in_and_session_values(self):
        # GIVEN / WHEN
        config = AmazonAuthConfig(data={
            "constants_class": "tests.test_constants.RegionOverrideConstants",
            "domain": "amazon.co.uk",
        })

        # THEN
        self.assertEqual("customflex", config.constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"])
        self.assertIn("openid.assoc_handle=customflex", config.constants.BASE_HEADERS["Referer"])
        self.assertEqual(["x-custom"], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)
        self.assertEqual("https://www.amazon.co.uk/?ref_=nav_custrec_signin",
                         config.constants.SIGN_IN_QUERY_PARAMS["openid.return_to"])


class RegionOverrideConstants(AuthConstants):
    SIGN_IN_QUERY_PARAMS = dict(AuthConstants.SIGN_IN_QUERY_PARAMS, **{"openid.assoc_handle": "customflex"})
    COOKIES_SET_WHEN_AUTHENTICATED = ["x-custom"]


class RequestCookiesOverrideConstants(AuthConstants):
    REQUEST_COOKIES = {"lc-acbfr": "fr_FR"}
