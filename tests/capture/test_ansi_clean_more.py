from loopster.capture.pipe_capture import capture_command


def read_text(p):
    return p.read_text(encoding="utf-8")


def test_csi_private_params_are_removed(tmp_path):
    # Sequences like CSI > 7 u and CSI < 1 u should be stripped
    payload = "\x1b[>7uHello\n\x1b[<1uWorld\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    assert "[>7u" not in text and "[<1u" not in text
    assert "Hello" in text and "World" in text


def test_cr_overwrite_truncates_prior_content(tmp_path):
    # Simulate a spinner/status overwritten by a shorter final message
    # Without explicit EL (K), we still want the final line without leftovers
    before = "codex thinking (3s • Esc to interrupt)"
    after = "42"
    payload = before + "\r" + after + "\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    # Final rendered line should be exactly the overwritten content
    assert any(line.strip() == after for line in text.splitlines()), text


def test_osc_sequences_are_stripped(tmp_path):
    # OSC to set terminal title followed by text
    # ESC ] 0;title BEL   then "Done\n"
    payload = "\x1b]0;My Title\x07Done\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    assert "My Title" not in text  # stripped
    assert any(line.strip() == "Done" for line in text.splitlines())


def test_cr_without_overwrite_does_not_truncate_line(tmp_path):
    # If a line writes text, then emits a CR and immediately a newline
    # without writing new characters, the original line content should
    # be preserved (not truncated to empty).
    payload = "Hello" + "\r" + "\n" + "World\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    lines = [ln.rstrip() for ln in text.splitlines() if ln is not None]
    # Ensure 'Hello' line is still present, followed by 'World'
    assert "Hello" in lines, text
    assert any(ln.strip() == "World" for ln in lines), text


def test_el_k_does_not_erase_prior_line_content(tmp_path):
    # Print a line, move to previous line (CPL), issue EL (K) to clear the
    # visual line, then move to next line and print another line. The transcript
    # should still contain the original content; EL should not delete history.
    # Sequence: 'Hello\n' then ESC[1F (prev line), ESC[K (erase to EOL), ESC[1E (next line), 'World\n'
    payload = "Hello\n" + "\x1b[1F" + "\x1b[K" + "\x1b[1E" + "World\n"
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r})\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    lines = [ln.rstrip() for ln in text.splitlines()]
    assert "Hello" in lines, text
    assert "World" in lines, text


def test_cr_overwrite_truncates_on_eof_without_newline(tmp_path):
    # Simulate spinner-like behavior that ends without a newline:
    # write a long status, CR, then a shorter final message, then exit.
    before = "Downloading something very large..."
    after = "Done"
    payload = before + "\r" + after
    cmd = (
        f"python -c \"import sys; sys.stdout.write({payload!r}); sys.stdout.flush()\""
    )
    log_path = tmp_path / "session.log"
    code = capture_command(cmd, str(log_path), mirror_to_stdout=False)
    assert code == 0
    text = read_text(log_path)
    # The last line should not contain leftover from the longer text
    last = text.splitlines()[-1]
    assert last.strip() == after, text
