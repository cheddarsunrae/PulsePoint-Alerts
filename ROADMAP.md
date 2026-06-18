# PulsePoint Alert Monitor Roadmap

This roadmap tracks planned improvements for PulsePoint Alert Monitor. The app is a supplemental backup alerting aid only and is not official dispatch, CAD, radio, pager, or a life-safety system.

## Current Alpha Focus

- Stabilize Active-vs-Recent incident parsing.
- Improve active incident signature tracking.
- Verify desktop/laptop alert behavior.
- Verify phone push behavior through Pushover and ntfy.
- Improve Windows usability and installer flow.
- Improve UI clarity for non-technical users.

## Completed / Working

- Local Flask web UI.
- PulsePoint Respond for Web monitoring.
- Agency and unit presets.
- Test mode.
- Active-section-only monitoring.
- Incident signature tracking.
- Laptop/desktop audible alert.
- ACK / Silence alert.
- Pushover emergency push support.
- ntfy urgent push support.
- Alert channel toggles for desktop and phone.
- Simulated active incident alert test.
- Alert history page.
- Logo and icon assets.
- Favicon / app icon integration.
- UI status colors.
- Basic popup help/tooltips.

## Near-Term Priority

### 1. Privacy Controls for Call Details

Status: phone-push call-detail visibility setting added.

Add a setting to control whether call details are included in phone push notifications.

Planned setting:

- Include call details in desktop alert/history: ON/OFF
- Include call details in phone push: ON/OFF — implemented

Reason:

Phone push notifications may appear on a lock screen. Users should be able to choose whether incident details such as address, call type, or unit list appear in phone notifications.

Recommended behavior:

- Desktop/history details: default ON
- Phone push details: user-configurable
- Public/shared releases should make the privacy impact clear

### 2. Active Incident Debug Page

Add a debug page showing:

- Active section detected: yes/no
- Raw Active section preview
- Units detected in Active
- Current incident signatures
- Last signature change time

Purpose:

Help troubleshoot PulsePoint layout changes and parser behavior.

### 3. Persistent Alert History

Status: local JSON persistence implemented.

Alert history now persists locally to disk and can be exported as CSV. Future work can add filtering.

Planned fields:

- Alert timestamp
- Unit(s)
- Incident signature
- Alert reason
- Desktop sent
- Phone sent
- Acknowledged
- ACK timestamp
- Source: monitor, simulation, manual test

### 4. Windows Desktop Shortcut Helper

Add installer support for:

- Creating a desktop shortcut
- Using the app .ico
- Opening the local app URL
- Optional auto-start behavior

### 5. Start-at-Login / Overnight Mode

Add optional Windows startup integration:

- Launch app at login
- Optionally start monitor automatically
- Keep Windows awake while monitoring

### 6. Config Export / Import

Status: implemented full export, redacted export, import, reset, and config path display.

Add UI controls for:

- Export config
- Import config
- Reset config
- Backup current config

### 7. Better Installer

Improve installer behavior:

- Check Python version
- Check Playwright install
- Copy app icon/logo/sound assets
- Create runtime folder
- Create shortcut
- Open app after install

## Medium-Term Improvements

- Native Windows packaging.
- System tray indicator.
- Packaged executable with app icon.
- Improved mobile-friendly UI.
- Theme support / dark mode.
- Multi-agency monitoring improvements.
- Multi-unit alert grouping.
- Per-unit alert settings.
- Alert snooze / mute window.
- Better parser tests using saved PulsePoint page samples.
- Optional local-only logs export.

## Security / Privacy Backlog

- Mask tokens by default in UI.
- Add clear warning for phone lock-screen exposure.
- Option to hide addresses from phone pushes.
- Option to include only unit/call type without address.
- Optional encrypted config storage later.
- Avoid logging full secrets or tokens.
- Clear test/simulation data from history.

## Release Milestones

### v0.1 Alpha

Goal: Working local technical preview.

- Windows-first local monitoring.
- Basic installer scripts.
- Desktop and phone alerting.
- Active incident detection.
- Alert history.
- Basic documentation.

### v0.2 Alpha

Goal: More reliable and user-friendly.

- Privacy controls.
- Debug page.
- Persistent history.
- Better installer.
- Desktop shortcut helper.

### v0.3 Beta

Goal: Normal-user install experience.

- One-command or packaged Windows install.
- Startup integration.
- Polished UI.
- Stronger parser test coverage.
- Config import/export.

### v1.0

Goal: Stable public release.

- Documented limitations.
- Tested install/update path.
- Robust alert behavior.
- User-facing safety disclaimers.
- Clear non-affiliation language.

## Process Improvements

- Local documentation guard added to remind/block developers when source, installer, or test changes are staged without related documentation or roadmap updates.


## Diagnostics Export

Status: implemented.

The app can export a troubleshooting ZIP containing redacted config, recent logs, alert history summary, monitor state, runtime paths, and Python/platform details.


## Parser Safety Tests

Status: implemented.

Added tests for Active/Recent section separation, monitored-unit detection, signature normalization, and call-detail summary cleanup.

The live monitor navigation was also changed from network-idle waits to DOM-content-loaded waits with a short settle delay to reduce hanging behavior.


## Named Agency Status Display

Status: implemented.

The top status bar now resolves active agency ID(s) to a saved agency preset name when available.


## Named Agency and Unit Status Display

Status: implemented.

The dashboard, config summary, and top status bar now resolve active agency ID(s) and active unit lists to saved preset names when available.


## Monitor Health Heartbeat

Status: implemented.

The UI now reports last check time, last success time, last refresh time, consecutive error count, last error, and Active-section detection status. Diagnostics export also includes these fields.


## Dashboard heartbeat scope fix

Status: implemented.

Fixed dashboard rendering so monitor-health variables are defined inside the dashboard view as well as the shared layout.


## Human-Readable Monitor Health

Status: implemented.

Health display now includes human-readable age text, green/yellow/red badge states, and stale-monitor detection based on poll interval.


## Dashboard Auto-Refresh

Status: implemented.

Dashboard auto-refreshes every 10 seconds. Configuration pages intentionally do not auto-refresh to avoid losing typed settings.
