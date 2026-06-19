from pulsepoint_alerts.app import create_app, start_monitor_if_needed


def test_dashboard_renders_without_heartbeat_scope_error():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Monitor Health" in response.data
    assert b"Last check" in response.data

def test_dashboard_has_auto_refresh_meta_tag():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'http-equiv="refresh"' in response.data
    assert b'content="10"' in response.data


def test_configuration_pages_do_not_auto_refresh():
    app = create_app()
    client = app.test_client()

    response = client.get("/setup")

    assert response.status_code == 200
    assert b'http-equiv="refresh"' not in response.data

def test_refresh_now_route_queues_manual_refresh_when_monitor_running():
    from pulsepoint_alerts.app import state

    app = create_app()
    client = app.test_client()

    with state.lock:
        state.monitor_running = True
        state.manual_refresh_requested = False

    response = client.post("/refresh-now")

    assert response.status_code == 302

    with state.lock:
        requested = state.manual_refresh_requested
        state.monitor_running = False
        state.manual_refresh_requested = False

    assert requested is True


def test_refresh_now_route_ignored_when_monitor_stopped():
    from pulsepoint_alerts.app import state

    app = create_app()
    client = app.test_client()

    with state.lock:
        state.monitor_running = False
        state.manual_refresh_requested = False

    response = client.post("/refresh-now")

    assert response.status_code == 302

    with state.lock:
        requested = state.manual_refresh_requested

    assert requested is False



def test_troubleshooting_page_renders():
    app = create_app()
    client = app.test_client()

    response = client.get("/troubleshooting")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Troubleshooting" in body
    assert "Monitor Health" in body
    assert "Export Diagnostics ZIP" in body


def test_status_bar_monitor_pill_is_clickable():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'action="/toggle-monitor"' in body
    assert "Click to start/stop monitor" in body


def test_header_displays_png_icon():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/static/app-icon.png" in body
    assert "brand-icon" in body


def test_toggle_monitor_starts_when_stopped(monkeypatch):
    from pulsepoint_alerts.app import state

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr("pulsepoint_alerts.app.threading.Thread", DummyThread)

    app = create_app()
    client = app.test_client()

    with state.lock:
        state.monitor_running = False
        state.monitor_stop.clear()

    response = client.post("/toggle-monitor")

    assert response.status_code == 302

    with state.lock:
        running = state.monitor_running
        state.monitor_running = False
        state.monitor_stop.set()

    assert running is True


def test_toggle_monitor_stops_when_running():
    from pulsepoint_alerts.app import state

    app = create_app()
    client = app.test_client()

    with state.lock:
        state.monitor_running = True
        state.monitor_stop.clear()

    response = client.post("/toggle-monitor")

    assert response.status_code == 302
    assert state.monitor_stop.is_set()

    with state.lock:
        state.monitor_running = False
        state.monitor_stop.clear()


def test_start_monitor_if_needed_returns_when_already_running():
    from pulsepoint_alerts.app import state

    with state.lock:
        state.monitor_running = True

    try:
        assert start_monitor_if_needed() is False
    finally:
        with state.lock:
            state.monitor_running = False


def test_toggle_monitor_stop_performs_standard_cleanup(monkeypatch):
    from pulsepoint_alerts.app import state

    cleanup_calls = []
    monkeypatch.setattr(
        "pulsepoint_alerts.app.silence_alert",
        lambda runtime_state: cleanup_calls.append(("silence", runtime_state)),
    )
    monkeypatch.setattr(
        "pulsepoint_alerts.app.set_keep_awake",
        lambda enabled: cleanup_calls.append(("keep_awake", enabled)),
    )

    app = create_app()
    client = app.test_client()

    with state.lock:
        state.monitor_running = True
        state.monitor_stop.clear()

    try:
        response = client.post("/toggle-monitor")

        assert response.status_code == 302
        assert state.monitor_stop.is_set()
        assert cleanup_calls == [("silence", state), ("keep_awake", False)]
    finally:
        with state.lock:
            state.monitor_running = False
        state.monitor_stop.clear()
