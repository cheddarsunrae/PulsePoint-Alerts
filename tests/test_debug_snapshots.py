from __future__ import annotations

from pulsepoint_alerts import runtime
from pulsepoint_alerts.monitor import maybe_record_active_missing_snapshot
from pulsepoint_alerts.runtime import RuntimeState


def test_record_debug_snapshot_writes_local_file(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "app_dir", lambda: tmp_path)
    state = RuntimeState()

    path = state.record_debug_snapshot("active section missing", "RECENT\nSome page text")

    assert path is not None
    assert path.exists()
    assert path.parent == tmp_path / "debug_snapshots"
    contents = path.read_text(encoding="utf-8")
    assert "Reason: active section missing" in contents
    assert "Warning:" in contents
    assert "RECENT\nSome page text" in contents


def test_missing_active_snapshot_is_one_shot_until_reset(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "app_dir", lambda: tmp_path)
    state = RuntimeState()

    saved = False
    saved = maybe_record_active_missing_snapshot(state, "first missing page", saved)
    saved = maybe_record_active_missing_snapshot(state, "second missing page", saved)

    files = sorted((tmp_path / "debug_snapshots").glob("*.txt"))
    assert saved is True
    assert len(files) == 1
    assert "first missing page" in files[0].read_text(encoding="utf-8")
    assert "second missing page" not in files[0].read_text(encoding="utf-8")


def test_missing_active_snapshot_can_save_again_after_found_reset(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "app_dir", lambda: tmp_path)
    state = RuntimeState()

    saved = False
    saved = maybe_record_active_missing_snapshot(state, "first streak", saved)

    # Simulate Active section being found in the monitor loop.
    saved = False

    saved = maybe_record_active_missing_snapshot(state, "second streak", saved)

    files = sorted((tmp_path / "debug_snapshots").glob("*.txt"))
    assert saved is True
    assert len(files) == 2
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "first streak" in combined
    assert "second streak" in combined
