from loopster.capture.pipe_capture import capture_command


def read_text(p):
    return p.read_text(encoding="utf-8")


def test_cup_upward_overwrite_with_spaces_does_not_erase_history(tmp_path):
    # Reproduce a TUI-style redraw that moves the cursor to an earlier line
    # and writes spaces over previously printed content. In a human-readable
    # transcript we want to preserve the earlier content (append-only view),
    # not erase history just because the TUI repainted the screen.
    #
    # 1) Print an initial line with content
    # 2) Move cursor to 1;1 (top-left) and write spaces and a newline
    # 3) Ensure the original content remains in the cleaned log
    payload = "Hello world\n" + "\x1b[1;1H" + (" " * 20) + "\n" + "Tail\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    # 'Hello world' should not be erased by the later CUP + spaces repaint
    assert "Hello world" in text, text
    # And the trailing content appears somewhere in the log
    assert "Tail" in text, text
