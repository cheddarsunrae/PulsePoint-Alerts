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

## Quick start - Windows

```powershell
cd C:\pulsepoint-alert
.\installers\windows\install.bat
.\installers\windows\start.bat
```

Then open:

```text
http://127.0.0.1:8765
```

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
