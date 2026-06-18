# Development Checklist

Before committing feature, UI, installer, parser, alerting, or documentation changes, check the following:

## Code

- Does the app still compile?
- Do tests pass?
- Did any config defaults change?
- Did any route, button, or workflow change?
- Did alert behavior change?
- Did parser behavior change?
- Did installer/runtime behavior change?

## Documentation

Update documentation when behavior changes.

Check:

- README.md
- ROADMAP.md
- docs/
- installer documentation
- troubleshooting notes
- screenshots or UI descriptions, if applicable

## Roadmap

Update ROADMAP.md when:

- a planned feature is completed
- a new idea is added
- a priority changes
- a feature is deferred
- a safety/privacy/security concern is discovered

## Changelog

Add a changelog entry when user-visible behavior changes.

Examples:

- new alert channel behavior
- parser changes
- new settings
- installer changes
- icon/logo integration
- privacy controls
- history/debug pages

## Privacy / Safety Review

Before committing alerting or notification changes, check:

- Could incident details appear on a lock screen?
- Are secrets or tokens exposed?
- Are logs storing anything sensitive?
- Is the non-affiliation / backup-only disclaimer still clear?
- Could the change create false confidence in the tool?

## Commit Hygiene

Before committing, run:

- python -m compileall -q src tests
- $env:PYTHONPATH="src"
- python -m pytest -q
- git status

Do not commit:

- real config files
- API tokens
- personal runtime logs
- .venv
- cache files
- local-only test artifacts

## Automated Documentation Guard

This repository includes a local documentation guard script:

- scripts/check_docs_updated.ps1
- scripts/install_git_hooks.ps1

Install the local pre-commit hook with:

    powershell -ExecutionPolicy Bypass -File .\scripts\install_git_hooks.ps1

The hook blocks commits when source, installer, or test files are staged without a README, ROADMAP, CHANGELOG, CONTRIBUTING, or docs update.

The hook does not automatically write documentation. It forces the developer to update documentation or make an intentional bypass.
