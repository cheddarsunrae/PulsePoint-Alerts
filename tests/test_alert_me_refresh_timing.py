from __future__ import annotations

from pulsepoint_alerts.monitor import effective_refresh_seconds, should_refresh_before_scan


def test_alert_me_refreshes_every_poll_interval():
    cfg = {
        "alert_profile": "alert_me",
        "poll_seconds": 10,
        "refresh_seconds": 300,
    }

    assert effective_refresh_seconds(cfg) == 10


def test_track_units_uses_configured_refresh_interval():
    cfg = {
        "alert_profile": "track_units",
        "poll_seconds": 10,
        "refresh_seconds": 300,
    }

    assert effective_refresh_seconds(cfg) == 300


def test_refresh_due_before_scan_when_page_age_exceeds_effective_interval():
    assert should_refresh_before_scan(now=100.0, last_refresh=89.0, refresh_seconds=10) is True
    assert should_refresh_before_scan(now=100.0, last_refresh=95.0, refresh_seconds=10) is False


def test_refresh_due_before_scan_when_no_refresh_has_been_recorded():
    assert should_refresh_before_scan(now=100.0, last_refresh=0.0, refresh_seconds=10) is True
