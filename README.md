# amazon-auth

[![Version](https://img.shields.io/pypi/v/amazon-auth)](https://pypi.org/project/amazon-auth)
[![Python Versions](https://img.shields.io/pypi/pyversions/amazon-auth.svg)](https://pypi.org/project/amazon-auth)
[![Coverage](https://img.shields.io/codecov/c/github/alexdlaird/amazon-auth)](https://codecov.io/gh/alexdlaird/amazon-auth)
[![Build](https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-auth/build.yml)](https://github.com/alexdlaird/amazon-auth/actions/workflows/build.yml)
[![Docs](https://img.shields.io/readthedocs/amazon-auth)](https://amazon-auth.readthedocs.io)
[![GitHub License](https://img.shields.io/github/license/alexdlaird/amazon-auth)](https://github.com/alexdlaird/amazon-auth/blob/main/LICENSE)

`amazon-auth` is an unofficial library that signs in to Amazon's consumer website (amazon.com and other Amazon sites)
and persists the session, so it can be reused from Python. It handles sign-in, OTP and MFA, challenges, and browser
sign-in. [`amazon-orders`](https://github.com/alexdlaird/amazon-orders) is built on it.

> **Note:** This package works by parsing Amazon's consumer-facing website. As Amazon provides no official API to use,
> older versions of this package may break at any time, so it's recommended that you use the latest version.

## Installation

`amazon-auth` is available on [PyPI](https://pypi.org/project/amazon-auth/) and can be installed and/or upgraded using `pip`:

```sh
pip install amazon-auth --upgrade
```

That's it! `amazon-auth` is now available as a package to your Python projects.

If pinning, be sure to use a wildcard for the [minor version](https://semver.org/) (e.g. `==0.2.*`, not `==0.2.0`) to
ensure you always get the latest stable release.

## Basic Usage

You'll use [`AmazonSession`](https://amazon-auth.readthedocs.io/api.html#amazonauth.session.AmazonSession) to sign in
to your Amazon account, then make requests with the signed-in session:

```python
from amazonauth.session import AmazonSession

amazon_session = AmazonSession("<AMAZON_EMAIL>",
                               "<AMAZON_PASSWORD>")
amazon_session.login()

response = amazon_session.get("https://www.amazon.com/gp/css/homepage.html")
print(response.parsed.title.text)
```

The most secure way to sign in is on Amazon's own page, in a browser window, so your credentials never need to be
stored (this requires the `browser` extra, `pip install amazon-auth[browser]`):

```python
from amazonauth.contrib.browser.playwright import PlaywrightBrowserLogin
from amazonauth.session import AmazonSession

amazon_session = AmazonSession()
PlaywrightBrowserLogin(amazon_session).login()
```

The session is persisted, so `AmazonSession().login()` reuses it without credentials.

## Documentation

For more advanced usage, `amazon-auth`'s official documentation is available
at [Read the Docs](https://amazon-auth.readthedocs.io).
