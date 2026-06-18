# Security Policy

## Sensitive data

Do not commit your real `config.json`. It may contain:

- Pushover app API tokens,
- Pushover user keys,
- ntfy tokens,
- private ntfy topics,
- agency/unit presets.

Use `config.example.json` for examples.

## Reporting vulnerabilities

Please open a private security advisory or contact the maintainers directly if you find a vulnerability that exposes credentials, enables code execution, or creates unsafe alerting behavior.

## Scope

Security issues include:

- credential leakage,
- unsafe local web exposure,
- malicious config injection,
- dependency vulnerability,
- unsafe packaging behavior,
- misleading alerting behavior that could create operational risk.
