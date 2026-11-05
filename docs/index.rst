****************************************************************************
Amazon Auth - Sign in to Amazon's consumer website from Python (and the CLI)
****************************************************************************

.. only:: builder_html

   .. image:: https://img.shields.io/pypi/v/amazon-auth
      :target: https://pypi.org/project/amazon-auth
   .. image:: https://img.shields.io/pypi/pyversions/amazon-auth.svg
      :target: https://pypi.org/project/amazon-auth
   .. image:: https://img.shields.io/codecov/c/github/alexdlaird/amazon-auth
      :target: https://codecov.io/gh/alexdlaird/amazon-auth
   .. image:: https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-auth/build.yml
      :target: https://github.com/alexdlaird/amazon-auth/actions/workflows/build.yml
   .. image:: https://img.shields.io/readthedocs/amazon-auth
      :target: https://amazon-auth.readthedocs.io
   .. image:: https://img.shields.io/github/license/alexdlaird/amazon-auth
      :target: https://github.com/alexdlaird/amazon-auth

``amazon-auth`` is an unofficial library that signs in to Amazon's consumer website and persists the session, so it
can be reused from Python or the command line. It handles sign-in, OTP and MFA, challenges, and browser sign-in.
`amazon-orders <https://amazon-orders.readthedocs.io>`_ is built on it.

.. note::

    This package works by parsing Amazon's consumer-facing website. As Amazon provides no official API to use, older
    versions of this package may break at any time, so it's recommended that you use the latest version.

Installation
============

``amazon-auth`` is available on
`PyPI <https://pypi.org/project/amazon-auth/>`__ and can be installed and/or upgraded
using ``pip``:

.. code:: sh

    pip install amazon-auth --upgrade

That's it! ``amazon-auth`` is now available as a package to your Python projects and from the command line.

If pinning, be sure to use a wildcard for the `minor version <https://semver.org/>`_ (e.g. ``==0.1.*``, not
``==0.1.0``) to ensure you always get the latest stable release.

Basic Usage
===========

You'll use :class:`~amazonauth.session.AmazonSession` to sign in to your Amazon account, then make requests with
the signed-in session through :func:`~amazonauth.session.AmazonSession.get` and
:func:`~amazonauth.session.AmazonSession.post`, which return the response alongside its parsed HTML.

.. code:: python

    from amazonauth.session import AmazonSession

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>")
    amazon_session.login()

    response = amazon_session.get("https://www.amazon.com/gp/css/homepage.html")
    print(response.parsed.title.text)

Command Line Usage
------------------

You can also sign in, check, and end the persisted session from the command line:

.. code:: sh

    amazon-auth login
    amazon-auth check-session --verify
    amazon-auth logout

.. _secure-sign-in:

Secure Sign-In
--------------

The most secure way to use ``amazon-auth`` is to sign in on Amazon's own page, in a browser window, so your
credentials never need to be stored:

.. code:: sh

    amazon-auth login --browser

The session is persisted, so neither the CLI nor the Python API needs credentials:

.. code:: python

    from amazonauth.session import AmazonSession

    amazon_session = AmazonSession()
    amazon_session.login()

This requires a display and the ``browser`` extra (see :ref:`Browser Automation <browser-installation>` to install it).

.. _automating-authentication:

Automating Authentication
-------------------------

Authentication can be automated by (in order of precedence) storing credentials in environment variables, passing them
to :class:`~amazonauth.session.AmazonSession`, or storing them in :class:`~amazonauth.conf.AmazonAuthConfig`. The
environment variables ``amazon-auth`` looks for are:

- ``AMAZON_USERNAME``
- ``AMAZON_PASSWORD``
- ``AMAZON_OTP_SECRET_KEY`` (see :attr:`~amazonauth.session.AmazonSession.otp_secret_key`)

Any other config value can be set the same way, as ``AMAZON_<KEY>`` (see :class:`~amazonauth.conf.AmazonAuthConfig`).

A configured username also applies to ``amazon-auth login --browser``: it's filled in and submitted for you, so the
browser opens on Amazon's password or passkey step. The browser never fills in your password.

Handling Challenges
-------------------

To enable **WAF auto-solve** via a third-party integration, install with the relevant extra:

.. code:: sh

    pip install amazon-auth[capsolver]
    pip install amazon-auth[anticaptcha]
    pip install amazon-auth[2captcha]

See :doc:`waf` for details.

To enable **browser-based challenge handling** (ACIC and JavaScript bot-detection pages) via
a headless browser, install with the ``browser`` extra:

.. code:: sh

    pip install amazon-auth[browser]

See :doc:`browser` for details.

For **legacy Captcha auto-solve** on Python <=3.12, install with ``captcha`` extra:

.. code:: sh

    pip install amazon-auth[captcha]

See :ref:`Login Challenges <login-challenges>` for details.

Sites
-----

``amazon-auth`` signs in to ``amazon.com`` by default. To sign in to another Amazon site, set the ``domain`` in the
:class:`config <amazonauth.conf.AmazonAuthConfig>` (e.g. ``amazon.co.uk``, or ``amazon.de``).

Each site has its own sign-in, so each keeps its own session: ``amazon.com``'s in ``cookies.json`` in the config
directory, and every other site's beside it, named for the site (e.g. ``cookies.amazon.de.json``). Signing in with
``--domain amazon.de`` leaves the ``amazon.com`` session as it is. An explicit ``cookie_jar_path`` is used for every
site.

Known Limitations
-----------------

- Amazon Business accounts are not supported
- Device not remembered for OTP
    - Amazon will sometimes re-prompt for OTP even when a device has been remembered.
    - The recommended workaround for this is persisting the :attr:`~amazonauth.session.AmazonSession.otp_secret_key`
      in the config or the environment so that re-prompts are auto-solved.

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api
   waf
   browser
   troubleshooting
