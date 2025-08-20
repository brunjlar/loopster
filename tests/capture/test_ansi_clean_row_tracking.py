from loopster.capture.pipe_capture import capture_command


def read_text(p):
    return p.read_text(encoding="utf-8")


def test_cnl_then_newline_does_not_crash(tmp_path):
    # Reproduce a scenario where the cursor moves to the next line(s)
    # using CNL (ESC [ n E) before a newline is printed. Previously,
    # this caused an IndexError in sanitize_ansi when referencing
    # cr_active[row] without ensuring the tracking arrays were long enough.
    payload = "\x1b[2E\nHello\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    # We only assert that capture completed and produced output, ensuring no crash.
    assert "Hello" in text

