===============
Troubleshooting
===============

Enable Debug Mode
-----------------

Enabling ``debug`` mode does a few main things:

1. Sets ``logger`` levels to ``DEBUG``
2. HTML pages will be saved locally

To enable ``debug`` mode in Python, you need to pass ``debug=True`` to
:class:`~amazonauth.session.AmazonSession`:

.. code-block:: python

    import logging

    from amazonauth.session import AmazonSession

    logging.basicConfig()

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>",
                                   debug=True)
    amazon_session.login()

Integrating with Amazon.com via scraping is complicated and requires ``form`` data from the
website's HTML. Before submitting a bug report or requesting a new feature, try running
``amazon-auth`` as described above, and if any console output or generated HTML
files are relevant to the issue, attach them to your request.

.. _login-challenges:

Login Challenges
----------------

Amazon may present JavaScript-based challenges during login that ``amazon-auth`` cannot solve via
HTTP requests alone. Several opt-in extras address these:

- **AWS WAF JavaScript challenge** — a ``[capsolver]``, ``[anticaptcha]``, or ``[2captcha]`` extra
  solves this automatically via a third-party API. See :doc:`waf` for setup.
- **AWS WAF JavaScript challenge (manual)** — the ``[browser]`` extra opens a visible browser
  window for you to solve the challenge yourself. Suitable when a display is available and you
  are able to handle the challenge interactively. See :ref:`manual-waf-solving` in :doc:`browser` for setup.
- **ACIC challenge** (``/ax/aaut/verify/ap/challenge``) or **JS bot-detection page**, including Akamai Bot
  Manager's interstitial (a blank page that verifies the browser and then reloads) — the
  ``[browser]`` extra handles these by running a headless browser. When the
  ACIC page also embeds a WAF challenge, a configured WAF solver extra solves it automatically as
  part of the same flow. See :doc:`browser` for setup.
- **Legacy text-based Captcha** — the ``[captcha]`` extra auto-solves via
  `amazoncaptcha <https://pypi.org/project/amazoncaptcha/>`_ (Python <=3.12 only;
  incompatible with Python 3.13+). Falls back to manual entry without this extra.

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-auth/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-auth/compare>`_.

To attempt to fully automate login, you need to minimize how often (if at all) you are presented with Captcha
challenges. There is no perfect workaround to this, as when and how challenges are presented is at the discretion of
Amazon, but there are at least a few ways you can try to reduce the likelihood you will be presented with
Captcha challenges:

- Ensure credentials are correct. Too many failed login attempts in a short period of time increases the chances of
  being given a Captcha challenge. Persisting authentication in the config or the environment (see :attr:`~amazonauth.session.AmazonSession.username`)
  can help ensure passwords are never entered incorrectly.
- Wait several hours (sometimes over a day is necessary) before trying again.
- Enable 2FA. One-time password (OTP) challenges during login can be auto-solved with :attr:`~amazonauth.session.AmazonSession.otp_secret_key`,
  and having this security measure enabled seems to reduce the frequency of Captcha challenges.
- Use a browser to manually solve the Captcha, as doing so may reduce the likelihood Amazon will continue to give you
  Captcha challenges from ``amazon-auth``.

    - In your browser, visit https://www.amazon.com/errors/validateCaptcha to solve a Captcha challenge while logged
      in to your account.

    - Logout of your account, then log back in. Amazon may present you with a different Captcha flow in this case,
      which may be the one that needs to be solved for them to stop prompting you.

    - Captcha challenges are more often presented to unknown devices. If possible, first manually login from a browser on
      the device on which you're using ``amazon-auth``.

Found an Unknown Page in the Sign-In Flow
-----------------------------------------

If you get an error during :func:`~amazonauth.session.AmazonSession.login()` saying you've encountered an unknown
page, you've found a page in the sign-in flow that we haven't. Amazon has many different routes through sign-in,
and is always adding more, so this is bound to happen. Hopefully you'll consider implementing the solution to this
sign-in flow and contributing it back to the repo.

Auth forms are actually relatively simple to implement. To get started investigating, `enable debug mode`_, then try
to login again. With ``debug`` mode enabled, the new page will be saved locally as an HTML file that you can open
and inspect.

Have a look at the HTML source of the new page, specifically the ``<form>`` tag, and look in ``forms.py`` to see how
other auth forms are implemented. You'll need to create a new class that inherits from
:class:`~amazonauth.forms.AuthForm`, override :func:`~amazonauth.forms.AuthForm.fill_form`, and manually pass
a list to :func:`~amazonauth.session.AmazonSession.auth_forms` that includes the new form.

Once you've implemented and tested the new form, `submit a PR <https://github.com/alexdlaird/amazon-auth/compare>`_
for maximum karma!
