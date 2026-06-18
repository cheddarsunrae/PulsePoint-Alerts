# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ctypes
import os

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040


def set_keep_awake(enabled: bool, keep_display_on: bool = False) -> None:
    if os.name != "nt":
        return
    if enabled:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        if keep_display_on:
            flags |= ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    else:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
