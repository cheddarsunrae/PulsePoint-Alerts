from __future__ import annotations

from pulsepoint_alerts import app as app_module


def test_troubleshooting_lists_debug_snapshots(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "debug_snapshots"
    snapshot_dir.mkdir()
    snapshot = snapshot_dir / "20260619_070000_active-section-missing.txt"
    snapshot.write_text("PulsePointer Alerter debug snapshot\nPAGE TEXT", encoding="utf-8")

    monkeypatch.setattr(app_module.state, "debug_snapshots_dir", lambda: snapshot_dir)

    client = app_module.create_app().test_client()
    response = client.get("/troubleshooting")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Debug Snapshots" in body
    assert snapshot.name in body
    assert f"/debug-snapshots/{snapshot.name}" in body


def test_debug_snapshot_view_is_read_only_and_escapes_content(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "debug_snapshots"
    snapshot_dir.mkdir()
    snapshot = snapshot_dir / "20260619_070000_active-section-missing.txt"
    snapshot.write_text("<script>alert('x')</script>\nCall details", encoding="utf-8")

    monkeypatch.setattr(app_module.state, "debug_snapshots_dir", lambda: snapshot_dir)

    client = app_module.create_app().test_client()
    response = client.get(f"/debug-snapshots/{snapshot.name}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "&lt;script&gt;alert" in body
    assert "<script>alert" not in body
    assert "Call details" in body


def test_debug_snapshot_view_blocks_path_traversal(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "debug_snapshots"
    snapshot_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(app_module.state, "debug_snapshots_dir", lambda: snapshot_dir)

    client = app_module.create_app().test_client()
    response = client.get("/debug-snapshots/../outside.txt")

    assert response.status_code == 404
