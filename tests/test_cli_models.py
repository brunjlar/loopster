import io
from contextlib import redirect_stdout

from loopster.cli import main


def run_cli(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_models_lists_known_items():
    code, out = run_cli(["models"])
    assert code == 0
    assert "OpenAI models:" in out
    assert "gpt-4o-mini" in out
    assert "gpt-5" in out
    assert "Google Gemini models:" in out
    assert "gemini-1.5-flash" in out
    assert "gemini-2.5-pro" in out
    assert "fake:" in out
