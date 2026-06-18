# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RuntimeState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    monitor_stop: threading.Event = field(default_factory=threading.Event)
    alert_stop: threading.Event = field(default_factory=threading.Event)
    monitor_running: bool = False
    alert_active: bool = False
    alert_reason: str = ""
    log_lines: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line, flush=True)
        with self.lock:
            self.log_lines.append(line)
            del self.log_lines[:-300]

    def logs(self, limit: int = 250) -> list[str]:
        with self.lock:
            return list(self.log_lines[-limit:])
