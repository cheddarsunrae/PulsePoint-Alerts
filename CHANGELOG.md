# Changelog

## 0.2.0-alpha.1 - 2026-06-19

### Added

- Added Pushover emergency receipt storage, desktop ACK retry cancellation, and phone-side Pushover ACK mirroring into local alert history.
- Documentation now identifies Pushover as the recommended provider for the full wake-up and future phone-acknowledgement workflow while preserving ntfy as the free/default path.
- Public PDF user guide for PulsePointer Alerter under `docs/`.
- Troubleshooting view for recent local debug snapshots.
- Alert profiles: Alert Me and Track Unit(s).
- Alert evidence snapshots for real monitor alerts.
- Troubleshooting page.
- Top-bar RUNNING / STOPPED monitor toggle.
- In-app PNG icon display.
- Cross-platform startup controls.
- Manual PulsePoint refresh button.
- Human-readable monitor health badges and heartbeat status.
- Dashboard-only auto-refresh.
- Config import/export and diagnostics ZIP export.
- Alert History CSV export.

### Changed

- Alert Me mode now refreshes PulsePoint before each poll scan to reduce stale-page alert lag; Dashboard copy now distinguishes page refresh from monitor polling.
- Dashboard ACK/Silence button is disabled when no alert is active and flashes red when an alert is active.
- Hardened Active-section incident parser to split incidents into blocks.
- Incident signatures now ignore unit-only lines to reduce duplicate alerts from unit roster/status changes.
- Improved Windows shortcut/startup handling.
- Improved roadmap and documentation structure.

### Fixed

- Preserved active incident baselines across missing-Active cycles so older active calls do not re-alert after a temporary missing-Active page state.
- Updated alert-profile tests to mock the receipt-aware Pushover ACK bridge path.
- Recaptured unit baseline when the monitored unit list changes while running, preventing already-active calls from alerting as new after CSV/watch-list edits.
- False alerts caused by neighboring non-monitored incidents.
- Duplicate-alert risk from unit status-marker changes.
- Lock-safe duplicate start/alert paths to avoid non-reentrant lock deadlocks.

