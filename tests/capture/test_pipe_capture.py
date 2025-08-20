from pathlib import Path

from loopster.capture.pipe_capture import capture_command


def test_capture_echo_hello(tmp_path):
    log_path = tmp_path / "session.log"
    code = capture_command('echo hello', str(log_path))
    assert code == 0
    data = Path(log_path).read_text().strip()
    assert "hello" in data

