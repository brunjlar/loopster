import io
from contextlib import redirect_stdout

from loopster.cli import main


def test_capture_help_mentions_timeout_and_cleaning():
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["capture", "--help"])
    out = buf.getvalue()
    assert code == 0
    assert "cleaned" in out.lower() or "human-readable" in out.lower()
    assert "124" in out  # exit code on timeout
    assert "timeout" in out.lower()
    assert "no-mirror" in out

