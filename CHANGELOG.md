# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/alexdlaird/amazon-auth/compare/0.2.6...HEAD)

### Added

- Add a browser-child environment hook to `PlaywrightBrowserLogin`.

## [0.2.6](https://github.com/alexdlaird/amazon-auth/compare/0.2.5...0.2.6) - 2026-11-10

### Deprecated

- `AmazonAuthConfig._default_data()`, renamed to `default_data()`.

## [0.2.5](https://github.com/alexdlaird/amazon-auth/compare/0.2.4...0.2.5) - 2026-11-10

### Deprecated

- `AuthConstants._apply_domain()`, renamed to `apply_domain()`.

### Fixed

- Bug fixes and stability improvements.

## [0.2.4](https://github.com/alexdlaird/amazon-auth/compare/0.2.3...0.2.4) - 2026-11-10

### Fixed

- Bug fixes and stability improvements.

## [0.2.3](https://github.com/alexdlaird/amazon-auth/compare/0.2.2...0.2.3) - 2026-11-09

### Fixed

- Bug fixes and stability improvements.

## [0.2.2](https://github.com/alexdlaird/amazon-auth/compare/0.2.1...0.2.2) - 2026-11-09

### Added

- [Building on `amazon-auth`](https://amazon-auth.readthedocs.io/downstream.html), for packages that extend its config, session, constants, selectors and CLI.

### Security

- `domain` must be an Amazon site over `https`, so credentials can't be sent to a mistyped or look-alike host.
- Redirects are never followed to `http://` or to re-send request data to another site, and drop `Origin` and `Referer` when they leave the site.
- Cookies from signing in with a browser keep `secure` and their expiry.
- The config file and `debug` output are only readable by the current user.

## [0.2.1](https://github.com/alexdlaird/amazon-auth/compare/0.2.0...0.2.1) - 2026-11-09

### Fixed

- `PlaywrightBrowserLogin.login()` no longer fails with `AttributeError` once sign-in completes in the browser, when used without `amazon-orders`. It verified the session against an `amazon-orders`-only URL.
- A config file whose `constants_class` or `selectors_class` names a package that isn't installed (for instance, one saved by `amazon-orders`, which shares the config file) falls back to the default class with a warning, instead of failing with `ModuleNotFoundError`.

## [0.2.0](https://github.com/alexdlaird/amazon-auth/compare/0.1.1...0.2.0) - 2026-11-09

### Removed

- The `amazon-auth` command and its `version` command. `amazon-auth` is a library to build on: a Click CLI built on it registers the `login`, `logout` and `check-session` commands from `amazonauth.cli`, as `amazon-orders` does.

## [0.1.1](https://github.com/alexdlaird/amazon-auth/compare/0.1.0...0.1.1) - 2026-11-09

### Security

- The `Host` header is no longer pinned, which sent Amazon's session cookies to any host requested, including through an off-site redirect.

## [0.1.0](https://github.com/alexdlaird/amazon-auth/compare/0.0.2...0.1.0) - 2026-11-05

### Added

- Sign-in, moved from `amazon-orders`, which now builds on it: `AmazonSession`, the sign-in forms, the WAF challenge solvers (`capsolver`, `anticaptcha` and `2captcha` extras), browser sign-in and challenge handling (`browser` extra), `AmazonAuthConfig`, `AuthConstants`, `AuthSelectors`, the `AmazonAuthError` exceptions, region data, and `select()` / `select_one()`.
- The `amazon-auth` CLI, with `login` (and `login --browser`), `logout`, `check-session` and `version`.
- A `captcha` extra, for legacy Captcha auto-solve on Python <=3.12, and an `lxml` extra, for `bs4_parser: lxml`.
- [Documentation](https://amazon-auth.readthedocs.io).

## [0.0.2](https://github.com/alexdlaird/amazon-auth/compare/0.0.1...0.0.2) - 2026-10-21

### Changed

- Placeholder description: being carved out of `amazon-orders`.

## [0.0.1](https://github.com/alexdlaird/amazon-auth/releases/tag/0.0.1) - 2026-10-21

### Added

- Placeholder release, reserving the `amazon-auth` name on PyPI.
