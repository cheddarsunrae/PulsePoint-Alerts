# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import plistlib
import sys

from .config import app_dir


@dataclass(frozen=True)
class StartAtLoginStatus:
    supported: bool
    enabled: bool
    platform_name: str
    path: Path | None
    detail: str


def home_directory() -> Path:
    return Path.home()


def source_repo_root() -> Path | None:
    """Return the source checkout root when running from the repository layout."""
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "src" / "pulsepoint_alerts").exists():
        return candidate
    return None


def launch_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "pulsepoint_alerts"]


def _platform_name() -> str:
    return platform.system()


def _windows_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return home_directory() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def start_at_login_path(system_name: str | None = None) -> Path | None:
    system_name = system_name or _platform_name()
    if system_name == "Windows":
        return _windows_startup_folder() / "PulsePoint Alert Monitor.cmd"
    if system_name == "Darwin":
        return home_directory() / "Library" / "LaunchAgents" / "com.cheddarsunrae.pulsepoint-alerts.plist"
    if system_name == "Linux":
        config_home = os.environ.get("XDG_CONFIG_HOME")
        base = Path(config_home) if config_home else home_directory() / ".config"
        return base / "autostart" / "pulsepoint-alert-monitor.desktop"
    return None


def _legacy_paths(system_name: str) -> list[Path]:
    if system_name == "Windows":
        return [_windows_startup_folder() / "PulsePoint Alert Monitor.lnk"]
    return []


def get_start_at_login_status() -> StartAtLoginStatus:
    system_name = _platform_name()
    path = start_at_login_path(system_name)
    if path is None:
        return StartAtLoginStatus(False, False, system_name or "Unknown", None, "This platform is not supported.")

    enabled_path = next((candidate for candidate in [path, *_legacy_paths(system_name)] if candidate.exists()), None)
    enabled = enabled_path is not None
    return StartAtLoginStatus(
        True,
        enabled,
        system_name,
        enabled_path or path,
        "Enabled for the current user." if enabled else "Disabled for the current user.",
    )


def _quote_windows_argument(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_desktop_argument(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def enable_start_at_login() -> StartAtLoginStatus:
    system_name = _platform_name()
    path = start_at_login_path(system_name)
    if path is None:
        raise RuntimeError(f"Start at login is not supported on {system_name or 'this platform'}.")

    path.parent.mkdir(parents=True, exist_ok=True)
    arguments = launch_arguments()

    if system_name == "Windows":
        repo_root = source_repo_root()
        start_bat = repo_root / "installers" / "windows" / "start.bat" if repo_root else None

        if start_bat and start_bat.exists():
            path.write_bytes(
                (
                    "@echo off\r\n"
                    f"cd /d {_quote_windows_argument(str(repo_root))}\r\n"
                    f"start \"\" /min {_quote_windows_argument(str(start_bat))}\r\n"
                ).encode("utf-8")
            )
        else:
            command = " ".join(_quote_windows_argument(argument) for argument in arguments)
            path.write_bytes(f"@echo off\r\nstart \"\" /min {command}\r\n".encode("utf-8"))
    elif system_name == "Darwin":
        runtime_dir = app_dir()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        repo_root = source_repo_root()
        payload = {
            "Label": "com.cheddarsunrae.pulsepoint-alerts",
            "ProgramArguments": arguments,
            "RunAtLoad": True,
            "KeepAlive": False,
            "StandardOutPath": str(runtime_dir / "start-at-login.log"),
            "StandardErrorPath": str(runtime_dir / "start-at-login-error.log"),
        }
        if repo_root is not None:
            payload["WorkingDirectory"] = str(repo_root)
        with path.open("wb") as stream:
            plistlib.dump(payload, stream)
    elif system_name == "Linux":
        command = " ".join(_quote_desktop_argument(argument) for argument in arguments)
        repo_root = source_repo_root()
        lines = [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=PulsePoint Alert Monitor",
            "Comment=Start PulsePoint Alert Monitor at login",
            f"Exec={command}",
        ]
        if repo_root is not None:
            lines.append(f"Path={repo_root}")
        lines.extend(
            [
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")

    return get_start_at_login_status()


def disable_start_at_login() -> StartAtLoginStatus:
    system_name = _platform_name()
    path = start_at_login_path(system_name)
    if path is None:
        raise RuntimeError(f"Start at login is not supported on {system_name or 'this platform'}.")

    for candidate in [path, *_legacy_paths(system_name)]:
        candidate.unlink(missing_ok=True)

    return get_start_at_login_status()
