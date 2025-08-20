import os
import re
import sys
import subprocess


def test_capture_uses_tempfile_when_no_output_provided():
    proc = subprocess.run(
        [sys.executable, "-m", "loopster", "capture", "--cmd", "echo hi"],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr

    # Expect a line announcing where the session was saved
    m = re.search(r"session saved to:\s*(.+)$", proc.stdout, re.MULTILINE)
    assert m, f"no 'session saved to' line in: {proc.stdout!r}"
    path = m.group(1).strip()

    # Path should exist and follow naming scheme
    assert os.path.exists(path)
    base = os.path.basename(path)
    assert base.startswith("loopster_") and base.endswith(".log")

    # File should contain the command output
    with open(path, "r", encoding="utf-8") as f:
        body = f.read()
    assert "hi" in body

