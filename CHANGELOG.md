# Changelog

## 0.2.0-alpha.1 - 2026-06-19

### Added

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

- Hardened Active-section incident parser to split incidents into blocks.
- Incident signatures now ignore unit-only lines to reduce duplicate alerts from unit roster/status changes.
- Improved Windows shortcut/startup handling.
- Improved roadmap and documentation structure.

### Fixed

- False alerts caused by neighboring non-monitored incidents.
- Duplicate-alert risk from unit status-marker changes.
- Lock-safe duplicate start/alert paths to avoid non-reentrant lock deadlocks.

