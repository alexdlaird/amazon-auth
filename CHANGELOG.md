# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/alexdlaird/amazon-auth/compare/0.2.0...HEAD)

### Fixed

- `PlaywrightBrowserLogin.login()` no longer fails with `AttributeError` once sign-in completes in the browser, when used without `amazon-orders`. It verified the session against an `amazon-orders`-only URL.

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
