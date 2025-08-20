import io
from contextlib import redirect_stdout
from pathlib import Path

from loopster.cli import main


def test_capture_accepts_out_alias(tmp_path):
    log_path = tmp_path / "alias.log"
    # Run the CLI with --out alias and ensure the file is written
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["capture", "--cmd", "echo hi", "--out", str(log_path), "--no-mirror"])
    assert code == 0
    assert log_path.exists()
    assert "hi" in Path(log_path).read_text()

