"""Cancellable, timeout-bounded subprocess execution without a shell.

Reader threads drain stdout/stderr continuously so a noisy tool cannot deadlock
on a full pipe.  Cancellation and timeout terminate the process and are
reported as data, never interpreted as a successful scan.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

_MAX_CAPTURE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    cancelled: bool = False
    output_truncated: bool = False


def _reader(stream, sink: list[bytes], truncated: list[bool]) -> None:
    total = 0
    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            if total < _MAX_CAPTURE_BYTES:
                remaining = _MAX_CAPTURE_BYTES - total
                sink.append(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[0] = True
            else:
                truncated[0] = True
            total += len(chunk)
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _decode(chunks: list[bytes]) -> str:
    return b"".join(chunks).decode("utf-8", errors="replace")


def run_command(
    argv: Sequence[str],
    *,
    cwd: str | Path | None,
    timeout_seconds: float,
    cancel_event: threading.Event | None = None,
    env_extra: Mapping[str, str] | None = None,
) -> CommandResult:
    if not argv or any(not isinstance(part, str) for part in argv):
        raise ValueError("命令参数必须是字符串列表")
    if timeout_seconds <= 0:
        raise ValueError("超时时间必须大于 0")
    if cancel_event is not None and cancel_event.is_set():
        return CommandResult(
            command=tuple(argv),
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            cancelled=True,
        )

    env = os.environ.copy()
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    if env_extra:
        env.update({str(key): str(value) for key, value in env_extra.items()})
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    start = time.monotonic()
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=False,
            env=env,
            creationflags=creationflags,
        )
    except OSError as exc:
        raise OSError(f"无法启动外部工具: {exc}") from exc

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_truncated: list[bool] = [False]
    stderr_truncated: list[bool] = [False]
    stdout_thread = threading.Thread(
        target=_reader, args=(process.stdout, stdout_chunks, stdout_truncated), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_reader, args=(process.stderr, stderr_chunks, stderr_truncated), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    cancelled = False
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            _terminate(process)
            break
        if time.monotonic() - start > timeout_seconds:
            timed_out = True
            _terminate(process)
            break
        time.sleep(0.05)

    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    stdout_thread.join(timeout=3)
    stderr_thread.join(timeout=3)
    duration = time.monotonic() - start
    return CommandResult(
        command=tuple(argv),
        returncode=process.returncode,
        stdout=_decode(stdout_chunks),
        stderr=_decode(stderr_chunks),
        duration_seconds=duration,
        timed_out=timed_out,
        cancelled=cancelled,
        output_truncated=stdout_truncated[0] or stderr_truncated[0],
    )


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
