from __future__ import annotations

import subprocess
from pathlib import Path


def capture_command(cmd: str, output_path: str) -> int:
    """
    Minimal, portable capture for a non-interactive command.
    Runs via bash -lc and writes stdout+stderr to output_path.
    Returns the exit code.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as f:
        proc = subprocess.Popen(
            ["bash", "-lc", cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        assert proc.stdout is not None
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            f.write(chunk)
        proc.wait()
        return proc.returncode

