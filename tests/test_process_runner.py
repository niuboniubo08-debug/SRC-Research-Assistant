from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from scanners.process_runner import run_command


def test_argument_list_does_not_use_shell(tmp_path: Path) -> None:
    value = "hello world; not-a-shell"
    result = run_command(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", value],
        cwd=tmp_path,
        timeout_seconds=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == value
    assert result.timed_out is False
    assert result.cancelled is False


def test_timeout_is_reported_and_process_is_terminated(tmp_path: Path) -> None:
    started = time.monotonic()
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        timeout_seconds=0.5,
    )
    assert result.timed_out is True
    assert result.cancelled is False
    assert time.monotonic() - started < 8


def test_cancellation_is_reported(tmp_path: Path) -> None:
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    started = time.monotonic()
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        timeout_seconds=10,
        cancel_event=cancel,
    )
    timer.cancel()
    assert result.cancelled is True
    assert result.timed_out is False
    assert time.monotonic() - started < 8
