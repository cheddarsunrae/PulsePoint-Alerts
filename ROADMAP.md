# PulsePoint Alert Monitor Roadmap

PulsePoint Alert Monitor is a Windows-first supplemental backup alerting aid for locally monitoring PulsePoint Respond for Web. It is not affiliated with PulsePoint Foundation, PulsePoint Respond, any public safety agency, CAD system, radio system, pager system, or official dispatch system. It is not a life-safety system.

## Current Status

Status: Alpha, locally functional.

The current build supports local monitoring, desktop alerting, Pushover/ntfy phone push, Active-section-only unit detection, persistent alert history, diagnostics export, saved agency/unit presets, setup pages, dashboard health monitoring, and Windows shortcut/startup helpers.

## Completed Alpha Features

### Core Monitoring

- Local Flask web UI.
- PulsePoint Respond for Web monitoring.
- Active-section-only monitoring.
- Recent/closed incident exclusion.
- Unit/apparatus matching.
- Incident signature tracking to reduce duplicate alerts.
- Manual PulsePoint refresh request from Dashboard.
- Monitor page loading hardened to avoid network-idle hangs.
- Parser safety tests for Active/Recent separation and monitored-unit detection.

### Alerting

- Laptop/desktop audible alert.
- ACK / Silence alert.
- Pushover emergency push support.
- ntfy urgent push support.
- Desktop alert enable/disable toggle.
- Phone push enable/disable toggle.
- Test Laptop Alert button.
- Test Phone Push button.
- Simulated active incident alert test.
- Phone push call-detail privacy toggle.

### UI / Usability

- Dashboard.
- Setup Wizard.
- Agencies page.
- Apparatus / Units page.
- Monitor Setup page.
- Alerts page.
- Logs page.
- Alert History page.
- Active Debug page.
- Config page.
- Popup help/tooltips.
- Color-coded Start/Stop/ACK/Test buttons.
- Start/Stop buttons grey out when unavailable.
- Dashboard-only auto-refresh.
- Human-readable monitor health age display.
- Green/yellow/red health badges.
- Named agency display in status areas.
- Named unit set display in status areas.
- Logo, favicon, and app icon integration.

### Runtime / Reliability

- Persistent alert history stored locally.
- Alert history CSV export.
- Runtime config path display.
- Config full export.
- Config redacted export.
- Config import.
- Config reset.
- Diagnostics ZIP export.
- Sleep prevention while monitoring.
- Monitor health heartbeat:
  - last check
  - last success
  - last refresh
  - active-section-found status
  - consecutive error count
  - last error
- Manual refresh queue for the running monitor.

### Windows Usability

- Windows desktop shortcut helper.
- Optional Windows Startup-folder shortcut.
- App icon used for shortcuts when available.
- Local runtime directory under `C:\pulsepoint-alert`.

### Process / Documentation

- README maintained with feature updates.
- Roadmap maintained with implementation status.
- Local documentation guard added.
- Pre-commit docs reminder/check available through `scripts/install_git_hooks.ps1`.

## Known Watch Items

- PulsePoint Web layout can change and break parsing.
- Current app uses the Flask development server for local-only operation.
- Manual refresh requests are processed on the next monitor loop cycle, not instantly mid-cycle.
- Existing active incidents are captured as baseline and do not alert until a new signature appears.
- Pushover emergency notifications repeat until acknowledged in Pushover.
- Phone lock-screen exposure depends on user privacy setting and phone notification settings.
- The separate `.docx` user guide may lag behind README unless regenerated.

## Near-Term Next Work

### 1. Better Windows Installer Flow

Goal: reduce manual setup steps.

Planned:

- Check Python version.
- Check Playwright install.
- Install dependencies.
- Copy app icon/logo/sound assets.
- Create runtime folder.
- Create desktop shortcut.
- Optionally enable Start-at-login.
- Open app after install.
- Show clear success/failure messages.

### 2. Token Masking in UI

Goal: prevent accidental exposure of push tokens.

Planned:

- Mask Pushover app token.
- Mask Pushover user key.
- Mask ntfy token.
- Add reveal/show option only when editing.
- Keep full export available for personal backup.
- Keep redacted export for sharing/troubleshooting.

### 3. Address / Detail Privacy Controls

Goal: more granular notification privacy.

Planned:

- Include full call details in phone push.
- Include only unit + call type.
- Hide address from phone push.
- Hide all call details from phone push.

Current status:

- Basic phone call-detail ON/OFF toggle implemented.

### 4. Better Alert History Filtering

Goal: make history easier to review.

Planned:

- Filter by source.
- Filter by acknowledged/unacknowledged.
- Filter by desktop/phone.
- Clear simulation/manual-test history.
- Export filtered CSV.

### 5. Saved PulsePoint Sample Tests

Goal: stronger parser regression coverage.

Planned:

- Save sanitized PulsePoint page text samples.
- Test parser against known Active/Recent layouts.
- Test multi-agency layouts.
- Test edge cases with punctuation, status labels, and repeated unit IDs.

## Medium-Term Roadmap

- Native Windows packaging.
- Packaged executable with app icon.
- System tray indicator.
- One-command installer.
- Mobile-friendly UI polish.
- Dark mode/theme support.
- Agency-scoped unit monitoring with per-unit Alert Me / Track Unit(s) profiles.
- Multi-unit incident grouping across mixed alert profiles.
- Alert snooze / mute window.
- Optional local-only logs export.
- Optional encrypted config storage.

## Security / Privacy Backlog

- Mask tokens by default in UI.
- Avoid logging full secrets or tokens.
- Add stronger lock-screen privacy warning.
- Option to hide addresses from phone pushes.
- Option to include only unit/call type without address.
- Redact sensitive fields in diagnostics by default.
- Clear test/simulation data from history.
- Optional encrypted config storage later.

## Release Milestones

### v0.1 Alpha

Goal: working local technical preview.

Status: substantially complete.

Includes:

- Windows-first local monitoring.
- Basic installer/start scripts.
- Desktop and phone alerting.
- Active incident detection.
- Alert history.
- Basic documentation.

### v0.2 Alpha

Goal: more reliable and user-friendly.

Status: in progress, mostly complete.

Includes:

- Privacy controls.
- Debug page.
- Persistent history.
- Desktop shortcut helper.
- Diagnostics export.
- Dashboard health monitor.
- Config import/export.

Remaining:

- Better installer flow.
- Token masking.

### v0.3 Beta

Goal: normal-user install experience.

Planned:

- One-command or packaged Windows install.
- Startup integration polish.
- Better installer validation.
- Polished UI.
- Stronger parser sample tests.
- Better privacy controls.

### v1.0

Goal: stable public release.

Planned:

- Documented limitations.
- Tested install/update path.
- Robust alert behavior.
- User-facing safety disclaimers.
- Clear non-affiliation language.
- Better privacy defaults.


## Incident Block Parser Fix

Status: implemented.

Replaced sliding-window unit matching with incident-block parsing. This prevents unrelated neighboring incidents from triggering alerts merely because an existing monitored-unit incident is nearby in the Active section. Unit status prefixes and unit-only responder list changes are normalized out of incident signatures. If incident boundaries cannot be identified, the parser fails safe instead of bundling the entire Active section.


## Alert Evidence Snapshots

Status: implemented.

Real monitor alerts persist local evidence snapshots containing the matched units, triggering incident blocks, signatures, configured monitor settings, and raw Active section text from the alert cycle. Diagnostics ZIP exports include recent evidence snapshots for post-incident troubleshooting.


## Troubleshooting Page

Status: implemented.

Added a read-only troubleshooting page with app/runtime health, install-path checks, shortcut status, monitor health, evidence/history counts, and quick export actions.


## Top-Bar Monitor Toggle

Status: implemented.

The RUNNING / STOPPED monitor status pill in the top bar can now be clicked to start or stop monitoring from any page. The program header also displays the PNG app icon directly in the UI.


## Alert Profiles

Status: implemented.

Added Alert Me and Track Unit(s) profiles. Alert Me retains looping desktop alerts, emergency/repeating phone pushes, ACK handling, history, and evidence. Track Unit(s) suppresses the desktop loop, uses low-priority non-emergency phone pushes with no ACK requirement, and preserves profile-tagged history and evidence. Profile selection is included throughout status displays, troubleshooting, diagnostics, and exports.


## Cross-Platform Start at Login

Status: implemented.

Added current-user interface controls for enabling and disabling start at login on Windows, macOS, and Linux. The app uses the Windows Startup folder, a macOS LaunchAgent, or an XDG autostart desktop entry and reports the active artifact on the Troubleshooting page.


## Agency-Scoped Unit Alert Profiles

Status: planned for later.

Allow each configured agency to have its own units, with every unit independently assigned to Alert Me or Track Unit(s). Unit IDs must be scoped to their agency so identical apparatus names in different feeds do not collide. Monitoring failures should remain isolated by agency.

For an incident matching a mixture of profiles, Alert Me should take precedence while history and evidence retain every matched unit, agency, and assigned profile in one grouped event. Existing global agency/unit/profile configurations should migrate automatically without changing current behavior.


## Version 0.2.0-alpha.1

Status: current alpha checkpoint.

This version reflects the alert-profile, parser-hardening, alert-evidence, troubleshooting, startup-control, and UI-control work completed after the original `0.1.0-alpha.1` technical preview.


## Start-at-login source checkout hardening

Status: implemented.

Windows start-at-login now prefers the repository `installers/windows/start.bat` when running from a source checkout, matching the known-good manual startup path. macOS and Linux startup files now include source-checkout working-directory hints when available.
