import sys
from pathlib import Path

from loopster.capture.pipe_capture import capture_command


def test_capture_interactive_echo(tmp_path):
    # Create a tiny interactive script
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

    # Run via capture, providing scripted inputs
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

