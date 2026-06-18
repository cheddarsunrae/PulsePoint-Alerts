# PulsePoint Alert Monitor

A local backup alerting tool that watches PulsePoint Respond for Web and alerts when a configured unit appears.

> **Backup alert only.** This is not official dispatch, not a pager, not CAD, not a radio, and not a life-safety system. Do not rely on it as your sole means of receiving emergency calls.

## Current status

`v0.1.0-alpha.1` — working prototype being refactored into a cross-platform app.

## Features

- Monitor one or more PulsePoint agency feeds.
- Watch one or more units/apparatus IDs.
- Test mode: alert on any new PulsePoint page activity.
- Laptop audible alert.
- Alert until acknowledged.
- Windows sleep prevention while monitor runs.
- Pushover emergency push support.
- ntfy urgent push support.
- Local web UI at `http://127.0.0.1:8765`.
- Saved agency and unit presets.
- First-run setup wizard.
- Installer copies the default alert sound into the runtime config folder.
- App version is shown in the UI.

## Quick start - Windows

From a cloned copy of this repository:

```powershell
cd C:\Users\Shane\Documents\GitHub\pulsepoint-alerts
.\installers\windows\install.bat
.\installers\windows\start.bat
```

Then open:

```text
http://127.0.0.1:8765
```

The Windows installer prepares the runtime folder:

```text
C:\pulsepoint-alert
```

and copies the default alert sound to:

```text
C:\pulsepoint-alert\alert.wav
```

## First-Run Setup Wizard

The app includes a first-run setup wizard at:

```text
http://127.0.0.1:8765/first-run
```

Use it to configure the minimum required settings:

1. Agency/feed name
2. PulsePoint agency ID(s)
3. Unit set name
4. Unit IDs to monitor
5. Poll interval
6. Test mode
7. Sleep prevention

After saving the wizard, configure laptop and phone alerts from the Alerts page.

## Normal use

1. Start the app.
2. Open the local web interface.
3. Configure agencies and unit sets.
4. Configure laptop and phone alerts.
5. Use test mode to confirm the alert path.
6. Turn test mode off for normal unit-watch mode.
7. Start the monitor.

## Development start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
python -m playwright install chromium
python -m pulsepoint_alerts
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
python -m pulsepoint_alerts
```

## Documentation

See `docs/`.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.

## Disclaimer

See `DISCLAIMER.md`.

## Safety, Affiliation, and Liability Disclaimer

PulsePoint Alert Monitor is a supplemental awareness and backup alerting aid only.

This project is not affiliated with, endorsed by, sponsored by, or approved by PulsePoint Foundation, PulsePoint Respond, or any public safety agency. “PulsePoint” and related names may be trademarks or service marks of their respective owners.

This software is not an official dispatch system, pager, CAD terminal, MDT, radio, station alerting system, or life-safety system. Do not rely on it as your sole or primary means of receiving emergency calls or dispatch information.

PulsePoint feeds may lag, omit incidents, omit units, change format, become unavailable, or fail. This tool may also fail due to operating system sleep, network connectivity, browser changes, API/provider failures, local configuration errors, notification-service failures, device settings, or software defects.

This software is provided “as is,” without warranty of any kind. The authors, maintainers, contributors, and affiliated entities are not responsible for missed calls, delayed responses, operational errors, injury, death, data loss, device malfunction, notification failure, employment consequences, disciplinary action, or any other damages or bad outcomes arising from use or misuse of this software.


## Privacy: Phone Push Call Details

The Alerts page includes a setting to control whether call details are included in phone push notifications.

When enabled, Pushover and/or ntfy messages may include incident details from the PulsePoint Active section. Depending on phone settings, these details may appear on the lock screen.

Turn this setting off if you want phone pushes to show only that a monitored unit alert occurred without including call details.


## Alert History Persistence

Alert history is saved locally in the app runtime folder as `alert_history.json`.

Default runtime locations:

- Windows: `C:\pulsepoint-alert\alert_history.json`
- macOS/Linux: `~/.pulsepoint-alerts/alert_history.json`

Alert history survives app restarts, can be cleared from the History page, and can also be exported as CSV.


## Alert Test History

Manual laptop alert tests, manual phone push tests, and simulated active incident alerts are written to Alert History.

Phone push test entries are marked as `manual_phone` and are automatically treated as acknowledged because they do not create a local laptop alert that needs to be silenced.

## Windows Shortcuts and Start-at-Login

PulsePoint Alert Monitor includes a Windows shortcut helper script.

### Create a Desktop Shortcut

From the repository folder, run:

    powershell -ExecutionPolicy Bypass -File .\installers\windows\create_shortcuts.ps1

This creates a desktop shortcut named:

    PulsePoint Alert Monitor

The shortcut launches the app through:

    installers\windows\start.bat

### Enable Start-at-Login

To launch the app automatically when Windows starts, run:

    powershell -ExecutionPolicy Bypass -File .\installers\windows\create_shortcuts.ps1 -StartAtLogin -NoDesktop

This creates a shortcut in the Windows Startup folder.

### Verify Start-at-Login

Run:

    C:\Users\Shane\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\PulsePoint Alert Monitor.lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "PulsePoint Alert Monitor.lnk"
    Test-Path C:\Users\Shane\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\PulsePoint Alert Monitor.lnk

Expected result:

    True

### Remove Start-at-Login

Run:

    powershell -ExecutionPolicy Bypass -File .\installers\windows\create_shortcuts.ps1 -RemoveStartAtLogin -NoDesktop

### Important Note

Start-at-login launches the app. To make the monitor itself start automatically after the app launches, enable the in-app setting:

    Auto-start monitor when app launches

This setting is located on the Monitor Setup page.

## Documentation Guard

Developers can install a local pre-commit documentation guard:

    powershell -ExecutionPolicy Bypass -File .\scripts\install_git_hooks.ps1

After installation, commits that change source, installer, or test files will require a related documentation or roadmap update.

This helps keep README.md, ROADMAP.md, CHANGELOG.md, CONTRIBUTING.md, and docs/ aligned with code changes.


## Config Backup, Import, and Reset

The Config page provides local configuration management.

Available actions:

- Export Full Config JSON
- Export Redacted Config JSON
- Import Config JSON
- Reset Config to Defaults
- View the active config file path

Full config exports may include sensitive values such as Pushover keys or ntfy tokens. Store full exports securely.

Use redacted exports for troubleshooting or sharing because token/key fields are replaced with `REDACTED`.

Resetting config does not delete alert history.


## Diagnostics Export

The Config page includes an **Export Diagnostics ZIP** button.

The diagnostics ZIP includes:

- diagnostics.json
- redacted_config.json
- recent_logs.txt
- alert_history_recent.json

The diagnostics export is intended for troubleshooting. It uses a redacted config file so Pushover keys and ntfy tokens are not included.

The full config export is still available separately for personal backup and restore, but full exports may contain secrets and should be stored securely.


## Monitor Parser Safety Tests

The test suite includes parser-safety tests for the PulsePoint Active/Recent split.

These tests verify that:

- Active incidents are scanned
- Recent/closed incidents are ignored
- monitored unit IDs are detected in Active incidents
- time/age noise is normalized out of incident signatures
- repeated lines are deduplicated in call-detail summaries

The live monitor uses `domcontentloaded` plus a short page-settle delay instead of waiting for full network idle, because PulsePoint can continue background network activity and cause network-idle waits to hang.


## Named Agency Status Display

The top status bar displays the active PulsePoint agency ID(s). When the active agency ID string matches a saved agency preset, the saved agency name is displayed beside the ID(s).

Example:

    Agency IDs: 37047 (AMR San Diego)

If no saved agency preset matches the active ID string, the status bar displays the raw agency ID(s).


## Named Agency and Unit Status Display

The dashboard, config summary, and top status bar display saved preset names when the active agency ID(s) or unit list match a saved preset.

Examples:

    Agency: 37047 (AMR San Diego)
    Units: E36, M231 (Station 36 / Jamul set)

If no saved preset matches, the app displays the raw agency ID(s) or unit list.
