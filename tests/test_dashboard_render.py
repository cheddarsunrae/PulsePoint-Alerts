from pulsepoint_alerts.app import create_app


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

