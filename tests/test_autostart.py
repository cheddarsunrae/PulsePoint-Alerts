import plistlib

import pytest

from pulsepoint_alerts import autostart


def test_windows_start_at_login_creates_and_removes_startup_command(monkeypatch, tmp_path):
    startup_root = tmp_path / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(startup_root))
    monkeypatch.setattr(autostart.platform, "system", lambda: "Windows")
    monkeypatch.setattr(autostart.sys, "executable", r"C:\Program Files\Python\python.exe")

    status = autostart.enable_start_at_login()

    assert status.enabled is True
    assert status.path.name == "PulsePoint Alert Monitor.cmd"
    contents = status.path.read_text(encoding="utf-8")
    assert '"C:\\Program Files\\Python\\python.exe"' in contents
    assert '"-m" "pulsepoint_alerts"' in contents

    status = autostart.disable_start_at_login()
    assert status.enabled is False
    assert not autostart.start_at_login_path().exists()


def test_macos_start_at_login_creates_launch_agent(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(autostart, "home_directory", lambda: tmp_path)
    monkeypatch.setattr(autostart, "app_dir", lambda: tmp_path / "runtime")
    monkeypatch.setattr(autostart.sys, "executable", "/usr/local/bin/python3")

    status = autostart.enable_start_at_login()

    with status.path.open("rb") as stream:
        payload = plistlib.load(stream)
    assert payload["Label"] == "com.cheddarsunrae.pulsepoint-alerts"
    assert payload["ProgramArguments"] == ["/usr/local/bin/python3", "-m", "pulsepoint_alerts"]
    assert payload["RunAtLoad"] is True

    assert autostart.disable_start_at_login().enabled is False


def test_linux_start_at_login_creates_xdg_desktop_entry(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart.platform, "system", lambda: "Linux")
    monkeypatch.setattr(autostart, "home_directory", lambda: tmp_path)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "/opt/PulsePoint Python/bin/python3")

    status = autostart.enable_start_at_login()

    contents = status.path.read_text(encoding="utf-8")
    assert status.path == tmp_path / ".config" / "autostart" / "pulsepoint-alert-monitor.desktop"
    assert 'Exec="/opt/PulsePoint Python/bin/python3" "-m" "pulsepoint_alerts"' in contents
    assert "X-GNOME-Autostart-enabled=true" in contents

    assert autostart.disable_start_at_login().enabled is False


def test_unsupported_platform_reports_clear_error(monkeypatch):
    monkeypatch.setattr(autostart.platform, "system", lambda: "FreeBSD")

    status = autostart.get_start_at_login_status()

    assert status.supported is False
    assert status.enabled is False
    with pytest.raises(RuntimeError, match="not supported"):
        autostart.enable_start_at_login()
