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

Alert history survives app restarts and can be cleared from the History page.
