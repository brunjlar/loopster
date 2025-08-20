from __future__ import annotations

import os
import subprocess
import sys
import locale
import time
from pathlib import Path
from typing import Iterable
from .ansi_clean import sanitize_ansi
import selectors


def _to_bytes(items: Iterable[str | bytes] | None) -> list[bytes]:
    if not items:
        return []
    return [it if isinstance(it, bytes) else it.encode() for it in items]


def capture_command(
    cmd: str,
    output_path: str,
    inputs: Iterable[str | bytes] | None = None,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
    mirror_to_stdout: bool = True,
    raw_output_path: str | None = None,
    prepend_header: str | None = None,
) -> int:
    """
    Capture a command's stdout/stderr to a file using pipes.

    - No PTY is allocated; programs will see non-interactive stdio.
    - Writes combined stdout+stderr to `output_path`.
    - Optionally feeds scripted `inputs` to stdin (then closes stdin).
    - Returns the process exit code; raises TimeoutError on timeout.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file: Path | None = Path(raw_output_path) if raw_output_path else None
    if raw_file is not None:
        raw_file.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=0,
    )

    # Preload inputs, if any, and close stdin to signal EOF when done.
    if proc.stdin is not None:
        if inputs:
            proc.stdin.write(b"".join(_to_bytes(inputs)))
            proc.stdin.flush()
        proc.stdin.close()

    start = time.monotonic()
    raw = bytearray()
    exit_code: int | None = None
    timed_out = False

    try:
        assert proc.stdout is not None
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        fd = proc.stdout.fileno()
        while True:
            # Check timeout first
            if timeout is not None and (time.monotonic() - start) > timeout:
                timed_out = True
                exit_code = 124
                try:
                    proc.terminate()
                except Exception:
                    pass
                break

            events = sel.select(timeout=0.1)
            if not events:
                # Poll process state to see if it exited
                if proc.poll() is not None:
                    break
                continue
            saw_eof = False
            for key, _ in events:
                try:
                    chunk = os.read(fd, 4096)
                except BlockingIOError:
                    chunk = b""
                if not chunk:
                    # EOF on pipe: unregister and break outer loop after this batch
                    try:
                        sel.unregister(proc.stdout)
                    except Exception:
                        pass
                    saw_eof = True
                    break
                raw.extend(chunk)
                if mirror_to_stdout:
                    buf = getattr(sys.stdout, "buffer", None)
                    if buf is not None:
                        buf.write(chunk)
                        buf.flush()
                    else:
                        enc = getattr(sys.stdout, "encoding", None) or locale.getpreferredencoding(False) or "utf-8"
                        sys.stdout.write(chunk.decode(enc, errors="replace"))
                        sys.stdout.flush()
            if saw_eof:
                break
    finally:
        # Always write whatever we captured so far
        decoded = raw.decode("utf-8", errors="replace")
        if raw_file is not None:
            try:
                raw_file.write_text(decoded, encoding="utf-8")
            except Exception:
                # Raw writing is best-effort; continue to write cleaned
                pass
        cleaned = sanitize_ansi(decoded)
        if prepend_header:
            header = prepend_header
            if not header.endswith("\n"):
                header += "\n"
            cleaned = header + cleaned
        out_file.write_text(cleaned, encoding="utf-8")
        # Try to reap the child; ignore errors
        try:
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=1)
            except Exception:
                pass

    if exit_code is not None:
        return exit_code
    return proc.returncode
