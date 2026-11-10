===========================
Building on ``amazon-auth``
===========================

``amazon-auth`` is meant to be built on: a package that reads more of Amazon's website, like |amazon-orders|_, gets
sign-in, the session, challenges, and the config file from ``amazon-auth``, and extends each by subclassing it. Every
class below is meant to be subclassed this way.

Config
------

Subclass :class:`~amazonauth.conf.AmazonAuthConfig` to add your package's config keys, and its default class paths
for :ref:`Constants and Selectors <downstream-constants-and-selectors>`. Set ``PACKAGE_NAME`` so messages that suggest
installing an extra name your package:

.. code:: python

    from amazonauth.conf import AmazonAuthConfig


    class MyPackageConfig(AmazonAuthConfig):
        PACKAGE_NAME = "my-package"

        @staticmethod
        def _default_data():
            return {
                **AmazonAuthConfig._default_data(),
                "constants_class": "mypackage.constants.Constants",
                "selectors_class": "mypackage.selectors.Selectors",
                "page_size": 20,
            }

Each key can then be set in the config file, passed in ``data``, or set with an ``AMAZON_<KEY>`` environment variable,
like ``amazon-auth``'s own.

Session
-------

Subclass :class:`~amazonauth.session.AmazonSession` and set ``CONFIG_CLASS``, so ``AmazonSession()`` with no config
builds yours. Your users then need only your package's import:

.. code:: python

    from amazonauth import session

    from mypackage.conf import MyPackageConfig


    class AmazonSession(session.AmazonSession):
        CONFIG_CLASS = MyPackageConfig

A package with no config keys of its own doesn't need either subclass, and can use ``amazon-auth``'s
:class:`~amazonauth.session.AmazonSession` as it is.

.. _downstream-constants-and-selectors:

Constants and Selectors
-----------------------

Subclass :class:`~amazonauth.constants.AuthConstants` for your package's URLs and formats, and
:class:`~amazonauth.selectors.AuthSelectors` for its CSS selectors, and name them as the defaults in your config (see
`Config`_). URLs that depend on the Amazon site go in
:func:`~amazonauth.constants.AuthConstants.apply_domain`, after ``amazon-auth``'s own:

.. code:: python

    from amazonauth.constants import AuthConstants


    class Constants(AuthConstants):
        SUBSCRIPTIONS_URL = f"{AuthConstants.BASE_URL}/subscriptions"

        def apply_domain(self, domain):
            super().apply_domain(domain)
            self.SUBSCRIPTIONS_URL = f"{self.BASE_URL}/subscriptions"

Command Line Interfaces
-----------------------

``amazon-auth`` has no command line of its own. A `Click <https://click.palletsprojects.com>`_ CLI built on it can
register its ``login``, ``logout`` and ``check-session`` commands, which read the session from
``ctx.obj["amazon_session"]``:

.. code:: python

    import click

    from amazonauth.cli import IOClick, check_session, login, logout

    from mypackage.session import AmazonSession


    @click.group()
    @click.pass_context
    def my_cli(ctx):
        ctx.ensure_object(dict)
        ctx.obj["amazon_session"] = AmazonSession(io=IOClick())


    my_cli.add_command(login)
    my_cli.add_command(logout)
    my_cli.add_command(check_session)

Shared Session and Config
-------------------------

Every package built on ``amazon-auth`` reads the same config file and session, in ``~/.config/amazonorders``, so
signing in once, with any of them, signs in all of them. A config file another package saved may name its own classes;
if one of those packages isn't installed, ``amazon-auth`` falls back to the default for that key, with a warning.
