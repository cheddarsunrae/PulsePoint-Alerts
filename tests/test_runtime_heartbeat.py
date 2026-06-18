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

