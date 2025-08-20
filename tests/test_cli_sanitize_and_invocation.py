import io
from contextlib import redirect_stdout
from pathlib import Path

from loopster.capture.ansi_clean import sanitize_ansi
from loopster.cli import main


def run_cli(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_sanitize_subcommand_uses_sanitizer(tmp_path):
    # Create a small raw sample including SGR styling and OSC title
    raw_path = tmp_path / "raw.txt"
    out_path = tmp_path / "out.txt"
    raw_text = "\x1b]0;My Title\x07" + "\x1b[31mRed\x1b[0m\nBlue\n"
    raw_path.write_text(raw_text, encoding="utf-8")

    code, out = run_cli(["sanitize", "--raw", str(raw_path), "--out", str(out_path)])
    assert code == 0
    assert "sanitized" in out

    expected = sanitize_ansi(raw_text)
    actual = out_path.read_text(encoding="utf-8")
    assert actual == expected


def test_capture_include_invocation_header(tmp_path):
    # Run a trivial command and confirm the header is prepended
    out_path = tmp_path / "cap.log"
    code, _ = run_cli([
        "capture",
        "--cmd",
        "python -c 'print(\"hi\")'",
        "--out",
        str(out_path),
        "--no-mirror",
        "--include-invocation",
    ])
    assert code == 0
    text = out_path.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    assert lines[0].startswith("loopster capture ")
    assert lines[1].startswith("[loopster] capturing:")
    assert lines[2].startswith("[loopster] log:")
    # And ensure payload is present after header
    assert any(ln.strip() == "hi" for ln in lines), text
