from __future__ import annotations

from pulsepoint_alerts import app as app_module


def _set_alert_state(active: bool, reason: str = "") -> None:
    with app_module.state.lock:
        app_module.state.alert_active = active
        app_module.state.alert_reason = reason


def test_dashboard_ack_button_disabled_when_no_alert():
    _set_alert_state(False, "")
    client = app_module.create_app().test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "btn-ack btn-ack-disabled" in body
    assert "disabled" in body
    assert "No Active Alert" in body
    assert "No active alert to acknowledge" in body


def test_dashboard_ack_button_flashes_when_alert_active():
    _set_alert_state(True, "Test alert reason")
    client = app_module.create_app().test_client()

    response = client.get("/")

    try:
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "btn-ack btn-ack-active" in body
        assert "ACK / Silence Alert" in body
        assert "Acknowledge and silence active alert" in body
        assert "Test alert reason" in body
    finally:
        _set_alert_state(False, "")
