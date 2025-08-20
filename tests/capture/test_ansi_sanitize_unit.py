from loopster.capture.ansi_clean import sanitize_ansi


def test_cup_upward_spaces_should_not_erase_history_unit():
    # Direct unit test against sanitizer: moving the cursor upward with CUP
    # and painting spaces should not erase already printed transcript lines.
    payload = "Hello world\n" + "\x1b[1;1H" + (" " * 20) + "\n" + "Tail\n"
    out = sanitize_ansi(payload)
    # Expect both pieces of content to remain visible in the cleaned log
    assert "Hello world" in out
    assert "Tail" in out

