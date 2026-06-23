import io
import json
import zipfile

from pulsepoint_alerts.alerting import send_phone_push_for_alert, trigger_alert
from pulsepoint_alerts.config import DEFAULT_CONFIG, alert_profile_label, normalize_alert_profile
from pulsepoint_alerts.runtime import RuntimeState


def config_for(profile: str) -> dict:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(
        {
            "alert_profile": profile,
            "desktop_alert_enabled": True,
            "phone_alert_enabled": True,
            "push_provider": "both",
        }
    )
    return cfg


def memory_state(monkeypatch) -> RuntimeState:
    state = RuntimeState()
    monkeypatch.setattr(state, "_write_alert_history", lambda events: None)
    monkeypatch.setattr(state, "_write_alert_evidence", lambda evidence: None)
    return state


def test_alert_me_keeps_desktop_phone_ack_history_and_evidence(monkeypatch):
    import pulsepoint_alerts.alerting as alerting

    state = memory_state(monkeypatch)
    phone_profiles = []
    started_threads = []

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            started_threads.append(True)

    monkeypatch.setattr(alerting, "load_config", lambda: config_for("alert_me"))
    monkeypatch.setattr(alerting, "send_phone_push_for_alert", lambda reason, runtime_state, profile: phone_profiles.append(profile))
    monkeypatch.setattr(alerting.threading, "Thread", DummyThread)

    trigger_alert("Unit alert", state, evidence={"matched_units": ["M231"]})

    event = state.alert_history()[-1]
    evidence = state.find_alert_evidence(event["evidence_id"])
    assert event["profile"] == "alert_me"
    assert event["desktop"] == "yes"
    assert event["phone"] == "yes"
    assert event["ack_required"] == "yes"
    assert event["acknowledged"] == "no"
    assert evidence["alert_profile"] == "alert_me"
    assert state.alert_active is True
    assert started_threads == [True]
    assert phone_profiles == ["alert_me"]


def test_track_units_skips_desktop_loop_and_ack_but_records_event(monkeypatch):
    import pulsepoint_alerts.alerting as alerting

    state = memory_state(monkeypatch)
    phone_profiles = []

    monkeypatch.setattr(alerting, "load_config", lambda: config_for("track_units"))
    monkeypatch.setattr(alerting, "send_phone_push_for_alert", lambda reason, runtime_state, profile: phone_profiles.append(profile))
    monkeypatch.setattr(
        alerting.threading,
        "Thread",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Track Unit(s) started a desktop alert thread")),
    )

    trigger_alert("Unit tracking update", state, evidence={"matched_units": ["M231"]})

    event = state.alert_history()[-1]
    evidence = state.find_alert_evidence(event["evidence_id"])
    assert event["profile"] == "track_units"
    assert event["desktop"] == "no"
    assert event["phone"] == "yes"
    assert event["ack_required"] == "no"
    assert event["acknowledged"] == "not_required"
    assert evidence["alert_profile"] == "track_units"
    assert state.alert_active is False
    assert phone_profiles == ["track_units"]


def test_track_units_uses_low_priority_non_emergency_pushes(monkeypatch):
    import pulsepoint_alerts.alerting as alerting

    state = RuntimeState()
    calls = []
    monkeypatch.setattr(alerting, "load_config", lambda: config_for("track_units"))
    def fake_pushover_with_receipt(title, message, runtime_state, **kwargs):
        calls.append(("pushover", title, kwargs))
        return True, ""

    monkeypatch.setattr(
        alerting,
        "send_pushover_with_receipt",
        fake_pushover_with_receipt,
    )
    monkeypatch.setattr(
        alerting,
        "send_ntfy",
        lambda title, message, runtime_state, **kwargs: calls.append(("ntfy", title, kwargs)),
    )

    send_phone_push_for_alert("Unit tracking update", state, profile="track_units")

    assert calls == [
        (
            "pushover",
            "PulsePoint Unit Tracking Update",
            {"emergency": False, "priority_override": -1},
        ),
        (
            "ntfy",
            "PulsePoint Unit Tracking Update",
            {"priority_override": 2, "allow_call": False},
        ),
    ]


def test_profile_is_visible_in_pages_csv_and_diagnostics(monkeypatch):
    import pulsepoint_alerts.app as app_module

    cfg = config_for("track_units")
    state = memory_state(monkeypatch)
    evidence_id = state.record_alert_evidence(
        {"alert_profile": "track_units", "matched_units": ["M231"]}
    )
    state.record_alert(
        "Tracking update",
        desktop_enabled=False,
        phone_enabled=True,
        evidence_id=evidence_id,
        profile="track_units",
        ack_required=False,
    )
    monkeypatch.setattr(app_module, "state", state)
    monkeypatch.setattr(app_module, "load_config", lambda: cfg)
    monkeypatch.setattr(app_module, "config_path", lambda: app_module.Path("config.json"))

    client = app_module.create_app().test_client()

    for path in ("/", "/alerts", "/history", f"/history/evidence/{evidence_id}", "/troubleshooting"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Track Unit(s)" in response.get_data(as_text=True)

    csv_body = client.get("/history/export.csv").get_data(as_text=True)
    assert "profile" in csv_body
    assert "track_units" in csv_body

    diagnostics_response = client.get("/diagnostics/export")
    with zipfile.ZipFile(io.BytesIO(diagnostics_response.data)) as archive:
        diagnostics = json.loads(archive.read("diagnostics.json"))
        history = json.loads(archive.read("alert_history_recent.json"))
        evidence = json.loads(archive.read("alert_evidence_recent.json"))

    assert diagnostics["settings_summary"]["alert_profile"] == "track_units"
    assert history[-1]["profile"] == "track_units"
    assert evidence[-1]["alert_profile"] == "track_units"


def test_alert_profile_normalization_and_labels():
    assert normalize_alert_profile("track_units") == "track_units"
    assert normalize_alert_profile("invalid") == "alert_me"
    assert alert_profile_label("alert_me") == "Alert Me"
    assert alert_profile_label("track_units") == "Track Unit(s)"
