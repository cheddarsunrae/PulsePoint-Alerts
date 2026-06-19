from pulsepoint_alerts.runtime import RuntimeState


def test_runtime_state_records_successful_check():
    state = RuntimeState()

    state.mark_check()
    state.mark_success(True)

    assert state.last_check_time
    assert state.last_success_time
    assert state.consecutive_errors == 0
    assert state.last_error == ""
    assert state.active_section_found is True


def test_runtime_state_records_error_count_and_message():
    state = RuntimeState()

    state.mark_error("example failure")
    state.mark_error("second failure")

    assert state.consecutive_errors == 2
    assert state.last_error == "second failure"


def test_runtime_state_records_refresh_time():
    state = RuntimeState()

    state.mark_refresh()

    assert state.last_refresh_time

def test_runtime_state_manual_refresh_request_is_consumed_once():
    state = RuntimeState()

    state.request_manual_refresh()

    assert state.consume_manual_refresh() is True
    assert state.consume_manual_refresh() is False



def test_runtime_alert_evidence_records_and_finds(monkeypatch, tmp_path):
    import pulsepoint_alerts.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "app_dir", lambda: tmp_path)

    state = RuntimeState()
    evidence_id = state.record_alert_evidence({
        "matched_units": ["M231"],
        "active_section_text": "ACTIVE\nMedical Emergency\n5:42 PM\nROCKY MOUNTAIN RD\nM231",
    })

    state.record_alert(
        "test alert",
        desktop_enabled=True,
        phone_enabled=True,
        source="monitor",
        evidence_id=evidence_id,
    )

    found = state.find_alert_evidence(evidence_id)

    assert found is not None
    assert found["matched_units"] == ["M231"]
    assert state.alert_history()[-1]["evidence_id"] == evidence_id


def test_runtime_clear_history_can_clear_evidence(monkeypatch, tmp_path):
    import pulsepoint_alerts.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "app_dir", lambda: tmp_path)

    state = RuntimeState()
    evidence_id = state.record_alert_evidence({"matched_units": ["M231"]})

    assert state.find_alert_evidence(evidence_id) is not None

    state.clear_alert_evidence()

    assert state.find_alert_evidence(evidence_id) is None
