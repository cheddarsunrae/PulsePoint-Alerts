from __future__ import annotations

import json

from pulsepoint_alerts import alerting
from pulsepoint_alerts.config import DEFAULT_CONFIG, save_config
from pulsepoint_alerts.runtime import RuntimeState


class FakeResponse:
    def __init__(self, body: dict, status: int = 200):
        self._body = json.dumps(body).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


def test_runtime_acknowledges_with_source_and_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSEPOINT_ALERT_DIR", str(tmp_path))
    state = RuntimeState()

    state.record_alert(
        "test alert",
        desktop_enabled=True,
        phone_enabled=True,
        source="monitor",
        profile="alert_me",
        ack_required=True,
        pushover_receipt="receipt123",
    )

    assert state.latest_pending_pushover_receipt() == "receipt123"

    state.acknowledge_latest_alert(
        source="pushover",
        detail="device=phone",
        ack_time="2026-01-01 00:00:00",
    )

    event = state.alert_history(1)[0]
    assert event["acknowledged"] == "yes"
    assert event["ack_time"] == "2026-01-01 00:00:00"
    assert event["ack_source"] == "pushover"
    assert event["ack_detail"] == "device=phone"
    assert event["pushover_acknowledged"] == "yes"
    assert state.latest_pending_pushover_receipt() == ""


def test_send_pushover_with_receipt_stores_emergency_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSEPOINT_ALERT_DIR", str(tmp_path))
    cfg = DEFAULT_CONFIG.copy()
    cfg["pushover_app_token"] = "app-token"
    cfg["pushover_user_key"] = "user-key"
    cfg["pushover_priority"] = 2
    save_config(cfg)

    def fake_urlopen(_req, timeout=15):
        return FakeResponse({"status": 1, "receipt": "receipt123", "request": "request123"})

    monkeypatch.setattr(alerting.urllib.request, "urlopen", fake_urlopen)

    state = RuntimeState()
    sent, receipt = alerting.send_pushover_with_receipt(
        "Title",
        "Message",
        state,
        emergency=True,
    )

    assert sent is True
    assert receipt == "receipt123"


def test_cancel_pushover_receipt_uses_cancel_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSEPOINT_ALERT_DIR", str(tmp_path))
    cfg = DEFAULT_CONFIG.copy()
    cfg["pushover_app_token"] = "app-token"
    save_config(cfg)

    captured = {}

    def fake_urlopen(req, timeout=15):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return FakeResponse({"status": 1, "request": "request123"})

    monkeypatch.setattr(alerting.urllib.request, "urlopen", fake_urlopen)

    state = RuntimeState()
    assert alerting.cancel_pushover_receipt("receipt123", state) is True
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/receipts/receipt123/cancel.json")


def test_pushover_receipt_status_reads_ack_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSEPOINT_ALERT_DIR", str(tmp_path))
    cfg = DEFAULT_CONFIG.copy()
    cfg["pushover_app_token"] = "app-token"
    save_config(cfg)

    def fake_urlopen(_req, timeout=15):
        return FakeResponse(
            {
                "status": 1,
                "acknowledged": 1,
                "acknowledged_at": 1760000000,
                "acknowledged_by": "user-key",
                "acknowledged_by_device": "phone",
            }
        )

    monkeypatch.setattr(alerting.urllib.request, "urlopen", fake_urlopen)

    state = RuntimeState()
    status = alerting.pushover_receipt_status("receipt123", state)

    assert status is not None
    assert status["acknowledged"] == 1
    assert status["acknowledged_by_device"] == "phone"
