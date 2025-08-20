from loopster.capture.pipe_capture import capture_command


def test_capture_times_out_and_writes_partial_log(tmp_path):
    # A command that sleeps beyond timeout
    cmd = "bash -lc 'echo start; sleep 5; echo end'"
    log_path = tmp_path / "session.log"
    # Set timeout to 0.5s
    code = capture_command(cmd, str(log_path), timeout=0.5, mirror_to_stdout=False)
    # Conventional timeout code
    assert code == 124
    text = log_path.read_text(encoding="utf-8")
    # We should have captured the initial echo but not necessarily 'end'
    assert "start" in text


def test_capture_times_out_with_no_output(tmp_path):
    # No output at all; ensure we don't hang on a blocking read
    cmd = "bash -lc 'sleep 5'"
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), timeout=0.5, mirror_to_stdout=False)
    assert code == 124
    # Log may contain shell/environment preamble from the host shell; we only
    # assert that the timeout occurred and a log file exists.
    assert log_path.exists() and log_path.stat().st_size >= 0
