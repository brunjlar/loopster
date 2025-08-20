import sys
from pathlib import Path

from loopster.capture.pipe_capture import capture_command


def test_passthrough_non_interactive(capsys, tmp_path):
    log_path = tmp_path / "session.log"
    code = capture_command("echo hello", str(log_path))
    assert code == 0
    # Ensure content made it to the log file
    assert "hello" in Path(log_path).read_text()
    # Ensure content was also printed to our stdout (passthrough)
    out = capsys.readouterr().out
    assert "hello" in out


def test_passthrough_interactive(capsys, tmp_path):
    script = tmp_path / "echo_interactive.py"
    script.write_text(
        """
import sys
print("Welcome", flush=True)
while True:
    print(">>> ", end="", flush=True)
    line = sys.stdin.readline()
    if not line:
        break
    line = line.strip()
    if line == "exit":
        print("bye", flush=True)
        break
    print(f"You said: {line}", flush=True)
        """.strip()
    )

    log_path = tmp_path / "session.log"
    code = capture_command(
        f"{sys.executable} {script}",
        str(log_path),
        inputs=["hello\n", "exit\n"],
    )

    assert code == 0
    data = Path(log_path).read_text()
    assert "Welcome" in data
    assert "You said: hello" in data
    assert "bye" in data

    out = capsys.readouterr().out
    assert "Welcome" in out
    assert "You said: hello" in out
    assert "bye" in out

