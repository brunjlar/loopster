import io
from contextlib import redirect_stdout

from loopster import __version__
from loopster.cli import main


def run_cli(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_help_lists_commands():
    code, out = run_cli(["--help"])
    assert code == 0
    # Check for key subcommands
    assert "run" in out
    assert "capture" in out
    assert "analyze" in out
    assert "summarize" in out
    assert "models" in out


def test_version_flag():
    code, out = run_cli(["--version"])
    assert code == 0
    assert __version__ in out


def test_subcommands_exit_zero():
    for sub in ["run", "capture", "analyze", "summarize", "models"]:
        code, _ = run_cli([sub])
        assert code == 0
