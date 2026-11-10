====================
Browser Automation
====================

Amazon sometimes presents JavaScript-based challenges during login that cannot be solved
by sending HTTP requests alone — the page requires a real browser to execute its scripts. The
``[browser]`` extra handles these challenges by running a headless browser and bridging the
resulting session back into ``amazon-auth``.

.. note::

    The ``[browser]`` extra also lets you sign in on Amazon's own page, see :ref:`Secure Sign-In <secure-sign-in>`.
    This page covers handling JavaScript sign-in challenges, not image Captchas. For legacy OCR-based
    image Captchas, see the ``[captcha]`` extra in :doc:`troubleshooting`. For the standalone AWS WAF JavaScript
    challenge (which can appear independently of an ACIC page), see :doc:`waf`.

Three challenge types are covered:

- **ACIC** (Amazon Challenge and Identity Component) — the ``#aa-challenge-page-captcha-container``
  challenge page. Amazon may embed a WAF token challenge, a visual grid Puzzle (e.g. "Choose all the
  buckets"), or both. These are passed to a WAF solver extra, when one is also configured, or handed to you
  (see below).
- **JS bot detection** — the ``"verify that you're not a robot / Enable JavaScript"`` page, and Akamai Bot
  Manager's interstitial, a blank page that verifies the browser and then reloads, which Amazon sometimes serves in
  place of a page. :class:`~amazonauth.contrib.browser.playwright.PlaywrightJSAuthForm` is a best-effort handler
  for these; effectiveness depends on whether the challenge resolves in a real browser without a
  visual puzzle.
- **AWS WAF (manual)** (Web Application Firewall) — :class:`~amazonauth.contrib.browser.playwright.PlaywrightManualWafForm` opens a visible browser
  window for you to solve the challenge yourself, suitable when a display is available.

.. _browser-installation:

Installation
------------

Add the ``[browser]`` extra:

.. code-block:: shell

    pip install amazon-auth[browser]

Configuration
-------------

Choosing a Browser
~~~~~~~~~~~~~~~~~~

``amazon-auth`` uses Chrome by default, then Edge if Chrome isn't installed, then Playwright's Chromium if
neither is. To use a different browser, set ``browser`` in the :class:`config <amazonauth.conf.AmazonAuthConfig>`.

Any browser `Playwright supports <https://playwright.dev/python/docs/browsers>`_ works, either one that's installed,
e.g. ``msedge``, or one Playwright installs, e.g. ``firefox``. For any other, set
``browser_executable_path`` to its path.

Registering Forms
~~~~~~~~~~~~~~~~~

Add one or both forms to ``auth_forms_classes`` in the :class:`config <amazonauth.conf.AmazonAuthConfig>`, in
this order: ``amazonauth.contrib.browser.playwright.PlaywrightAcicForm``, then
``amazonauth.contrib.browser.playwright.PlaywrightJSAuthForm``.

:class:`~amazonauth.contrib.browser.playwright.PlaywrightAcicForm` handles the ACIC challenge
page and should be registered first. :class:`~amazonauth.contrib.browser.playwright.PlaywrightJSAuthForm`
is the best-effort fallback for the pure JS bot-detection page and Akamai's interstitial, and should be registered
after.

.. _manual-waf-solving:

Manual WAF Solving
------------------

:class:`~amazonauth.contrib.browser.playwright.PlaywrightManualWafForm` opens a **visible**
browser window, lets you solve the WAF challenge yourself, and automatically harvests the
resulting cookies once the browser navigates away from the challenge page.

Because it requires a display and a user at the keyboard, it is intended for local/interactive
use only — not headless environments.

Add ``amazonauth.contrib.browser.playwright.PlaywrightManualWafForm`` to ``auth_forms_classes`` in the
:class:`config <amazonauth.conf.AmazonAuthConfig>`. It can be combined with ``PlaywrightAcicForm``, which then also
hands you any challenge embedded in the ACIC page (see `Combining with a WAF Solver`_).

Combining with a WAF Solver
---------------------------

Amazon sometimes embeds challenges inside the ACIC page — either a WAF token challenge, a visual
grid Puzzle (e.g. "Choose all the buckets"), or both. When this happens, the headless browser alone
cannot solve them, so ``PlaywrightAcicForm`` passes them on:

- **Manual** — register ``PlaywrightManualWafForm`` alongside ``PlaywrightAcicForm``. The ACIC
  browser itself opens visibly and hands the embedded challenge — whether a WAF token challenge or
  a visual grid Puzzle — to you to solve yourself.

- **Automated** — register a :doc:`WAF solver extra <waf>` alongside ``PlaywrightAcicForm``.
  ``PlaywrightAcicForm`` passes embedded challenges to it, without additional configuration.
  ``PlaywrightJSAuthForm`` is only needed here for Akamai's interstitial, since the JS bot-detection page is a WAF
  challenge, which goes to the WAF solver extra.

When more than one is registered, a challenge goes to each in the order they're listed in ``auth_forms_classes``, until
one handles it. That holds for a standalone WAF challenge too. For instance, a WAF solver extra and then
``PlaywrightManualWafForm`` hands you the challenge when the solver can't handle it, and ``PlaywrightManualWafForm`` and
then a WAF solver extra lets you solve it while you're at the machine, and the solver when there's no display.

Customizing the Sign-In
-----------------------

To customize the sign-in, subclass :class:`~amazonauth.contrib.browser.playwright.PlaywrightBrowserLogin` and
override its hooks, like ``on_sign_in_page()`` and ``wait_for_sign_in()``. Set ``headless`` to ``True`` if no browser
window is needed.

.. code-block:: python

    from amazonauth.contrib.browser.playwright import PlaywrightBrowserLogin


    class MyBrowserLogin(PlaywrightBrowserLogin):
        def on_sign_in_page(self, context, page):
            ...

        def wait_for_sign_in(self, context, page, timeout):
            ...

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-auth/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-auth/compare>`_.
