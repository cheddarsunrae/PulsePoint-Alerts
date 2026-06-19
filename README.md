# PulsePoint Alert Monitor

A local backup alerting tool that watches PulsePoint Respond for Web and alerts when a configured unit appears.

> **Backup alert only.** This is not official dispatch, not a pager, not CAD, not a radio, and not a life-safety system. Do not rely on it as your sole means of receiving emergency calls.

## Current status

`v0.1.0-alpha.1` — working prototype being refactored into a cross-platform app.

## Features

- Monitor one or more PulsePoint agency feeds.
- Watch one or more units/apparatus IDs.
- Choose Alert Me or Track Unit(s) behavior for monitored-unit activity.
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


## Alert Profiles

Choose the active profile on the Alerts page:

- **Alert Me** keeps the full alert workflow: enabled laptop/desktop looping alerts, emergency or repeating phone pushes, ACK/Silence requirements, history, and evidence.
- **Track Unit(s)** records monitored-unit activity without starting the looping desktop alert. Enabled phone pushes use low-priority, non-emergency delivery and do not request ntfy calling. Tracking events require no ACK while still retaining history and evidence.

The selected profile is shown on the Alerts page, Dashboard, top status bar, History, Evidence, Troubleshooting, diagnostics, and exported data. Existing configurations default to Alert Me.


## Alert History Persistence

Alert history is saved locally in the app runtime folder as `alert_history.json`.

Default runtime locations:

- Windows: `C:\pulsepoint-alert\alert_history.json`
- macOS/Linux: `~/.pulsepoint-alerts/alert_history.json`

Alert history survives app restarts, can be cleared from the History page, and can also be exported as CSV.


## Alert Test History

Manual laptop alert tests, manual phone push tests, and simulated active incident alerts are written to Alert History.

Phone push test entries are marked as `manual_phone` and as not requiring acknowledgement because they do not create a local laptop alert that needs to be silenced.

## Windows Shortcuts and Start-at-Login

PulsePoint Alert Monitor includes a Windows shortcut helper script.

The Troubleshooting page also provides cross-platform **Enable Start at Login** and **Disable Start at Login** controls. These use the current user's Windows Startup folder, macOS LaunchAgents, or Linux XDG autostart directory. No administrator access is required.

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


## Monitor Health Heartbeat

The dashboard and top status bar include monitor-health fields so the user can tell whether the monitor is actively checking PulsePoint.

Displayed health fields include:

- Last check time
- Last successful check time
- Last page refresh time
- Consecutive error count
- Last error
- Whether the Active section was found during the latest successful unit-mode scan

These fields are also included in the diagnostics ZIP.


## Human-Readable Monitor Health

The monitor-health display uses human-readable age text and color-coded health badges.

Health states:

- STOPPED: monitor is not running
- WAITING: monitor is running but no successful check has completed yet
- HEALTHY: recent successful check and no consecutive errors
- DEGRADED: one or two consecutive errors
- ERROR: three or more consecutive errors
- STALE: last successful check is older than the stale threshold

The stale threshold is calculated from the configured poll interval.


## Dashboard Auto-Refresh

The Dashboard auto-refreshes every 10 seconds so monitor health, last-check time, error count, and status badges stay current without manual browser refresh.

Configuration pages do not auto-refresh. This prevents losing typed settings while editing agencies, units, alerts, or config values.


## Manual PulsePoint Refresh

The Dashboard includes a **Refresh PulsePoint Now** button.

This button requests an immediate reload of the PulsePoint page on the next monitor cycle. It does not restart the monitor and does not change configuration.

The button is disabled when the monitor is stopped.


## Dashboard Health Layout

The top status bar is intentionally kept as an at-a-glance summary:

- Monitor
- Health
- Alert
- Agency
- Units

Detailed health information is shown in the Dashboard Monitor Health card to avoid duplicating too much information across the page.


## Incident Block Parser

The monitor splits the PulsePoint Active section into incident-sized blocks before looking for monitored units.

This prevents a monitored unit on one incident from being bundled with unrelated neighboring incidents. Earlier sliding-window parsing could cause false alerts when a new nearby incident appeared above or below an existing monitored-unit incident.

Incident signatures ignore unit-only lines so responder-list changes, unit-status marker changes, or unit ordering changes do not create duplicate alerts for the same incident.

If incident boundaries cannot be identified, the parser fails safe rather than bundling the entire Active section into one incident.


## Alert Evidence Snapshots

Real monitor alerts save a local evidence snapshot at the moment of alert.

Evidence snapshots include the matched monitored units, new incident signatures, triggering incident block text, configured units, agency IDs, signature method, and the raw PulsePoint Active section from that check cycle.

Alert History links to evidence snapshots when available. Diagnostics ZIP exports include recent alert evidence snapshots as `alert_evidence_recent.json`.

Evidence may contain call details or addresses from PulsePoint Active and should be treated as sensitive troubleshooting data.


## Troubleshooting Page

The app includes a read-only Troubleshooting page showing app version, Python/platform information, Playwright package status, runtime paths, shortcut status, monitor health, configured units, alert history count, evidence snapshot count, and quick export buttons for diagnostics, alert history, and redacted config.


## Top-Bar Monitor Toggle

The RUNNING / STOPPED monitor pill in the top status bar is clickable. Clicking it starts or stops the monitor without returning to the Dashboard.

The app header also displays the PNG app icon inside the program UI. This is separate from the favicon and Windows shortcut `.ico`.


## Current Version

Current alpha version: `0.2.0-alpha.1`

See `CHANGELOG.md` for release notes.


### Start-at-login source checkout behavior

When running from a source checkout on Windows, the Start at Login control uses `installers/windows/start.bat` so startup launches the app through the same tested path used for manual startup. If the app is packaged or installed differently, it falls back to `python -m pulsepoint_alerts`.
