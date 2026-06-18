# Contributing

Contributions are welcome.

## Priorities

1. Reliability and safety.
2. Clear user experience.
3. Cross-platform support.
4. Good documentation.
5. Low-friction installation.

## Ground rules

- Keep the disclaimer prominent.
- Do not add features that imply this is official dispatch.
- Do not hard-code real agency credentials, private topics, or tokens.
- Keep `config.json` out of commits.
- Prefer small, reviewable pull requests.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e .[dev]
python -m playwright install chromium
python -m pulsepoint_alerts
```

Then open:

```text
http://127.0.0.1:8765
```

## Documentation and Roadmap Updates

When making user-visible changes, update the relevant documentation in the same commit or pull request.

Check:

- README.md
- ROADMAP.md
- docs/
- docs/development-checklist.md
- installer documentation
- troubleshooting notes

Roadmap items should be marked complete, deferred, or updated as the project evolves.
