import io
from contextlib import redirect_stdout
from pathlib import Path

from loopster.cli import main


def test_capture_writes_raw_and_clean(tmp_path):
    raw_path = tmp_path / "raw.log"
    clean_path = tmp_path / "clean.log"

    # Emit SGR colored text so raw contains ESC while cleaned does not
    cmd = "python -c \"import sys; sys.stdout.write('\\x1b[32mhi\\x1b[0m\\n')\""

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main([
            "capture",
            "--cmd",
            cmd,
            "--out",
            str(clean_path),
            "--raw",
            str(raw_path),
            "--no-mirror",
        ])
    assert code == 0

    assert raw_path.exists()
    assert clean_path.exists()

    raw_text = Path(raw_path).read_text(encoding="utf-8")
    clean_text = Path(clean_path).read_text(encoding="utf-8")

    # Raw should contain ESC; cleaned should not
    assert "\x1b[" in raw_text
    assert "\x1b[" not in clean_text
    assert "hi" in clean_text

