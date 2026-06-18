from pulsepoint_alerts.app import create_app


def test_dashboard_renders_without_heartbeat_scope_error():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Monitor Health" in response.data
    assert b"Last check" in response.data
