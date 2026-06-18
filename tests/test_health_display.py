from datetime import datetime, timedelta

from pulsepoint_alerts.app import age_display, monitor_health_label, timestamp_age_seconds


def test_age_display_handles_never():
    assert age_display("never") == "never"
    assert timestamp_age_seconds("never") is None


def test_age_display_handles_recent_timestamp():
    stamp = (datetime.now() - timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S")
    result = age_display(stamp)

    assert result.endswith("sec ago")


def test_monitor_health_stopped_when_not_running():
    label, css = monitor_health_label(False, "never", 0, 5)

    assert label == "STOPPED"
    assert css == "status-stopped"


def test_monitor_health_waiting_when_running_without_success():
    label, css = monitor_health_label(True, "never", 0, 5)

    assert label == "WAITING"
    assert css == "status-warn"


def test_monitor_health_error_after_three_errors():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label, css = monitor_health_label(True, stamp, 3, 5)

    assert label == "ERROR"
    assert css == "status-alert-active"


def test_monitor_health_stale_when_last_success_is_old():
    old = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    label, css = monitor_health_label(True, old, 0, 5)

    assert label == "STALE"
    assert css == "status-alert-active"


def test_monitor_health_healthy_when_recent_success_and_no_errors():
    recent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label, css = monitor_health_label(True, recent, 0, 5)

    assert label == "HEALTHY"
    assert css == "status-running"
