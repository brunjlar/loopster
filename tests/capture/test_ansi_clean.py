import sys
from loopster.capture.pipe_capture import capture_command


def read_text(p):
    return p.read_text(encoding="utf-8")


def test_capture_strips_sgr_and_keeps_text(tmp_path):
    # Print green "hello" using SGR, then reset, then newline
    cmd = (
        "python -c \"import sys; sys.stdout.write('\\x1b[32mhello\\x1b[0m\\n')\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    assert "\x1b" not in text  # no raw escapes
    assert "hello" in text


def test_capture_handles_cuf_cursor_forward_as_spaces(tmp_path):
    # Write 'to', move cursor forward 1, then write 'quit' → expect at least one space
    cmd = (
        "python -c \"import sys; sys.stdout.write('to'); sys.stdout.write('\\x1b[1C'); sys.stdout.write('quit\\n')\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    assert "to quit" in text, text


def test_capture_handles_carriage_return_overwrite(tmp_path):
    # Typical progress output: 'Downloading' then CR then 'Done' should show both lines sensibly
    cmd = (
        "python -c \"import sys; sys.stdout.write('Downloading...'); sys.stdout.write('\\r'); sys.stdout.write('Done\\n')\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    # At minimum, final line should be 'Done'
    assert any(line.strip() == 'Done' for line in text.splitlines()), text
