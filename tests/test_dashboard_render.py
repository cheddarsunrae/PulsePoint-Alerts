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

