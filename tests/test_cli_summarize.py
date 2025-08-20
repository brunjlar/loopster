import io
from contextlib import redirect_stdout
from pathlib import Path

from loopster.cli import main


def run_cli(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_summarize_with_fake_model(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    log.write_text("did things\n")

    code, out = run_cli([
        "summarize",
        "--log",
        str(log),
        "--format",
        "text",
        "--model",
        "fake:test",
    ])
    assert code == 0
    assert out.strip() == "OK"


def test_summarize_missing_api_key_message(tmp_path, monkeypatch):
    # Ensure no key set for OpenAI
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    log = tmp_path / "log.txt"
    log.write_text("did things\n")

    code, out = run_cli([
        "summarize",
        "--log",
        str(log),
        "--format",
        "text",
        "--model",
        "gpt-4o-mini",
    ])
    assert code == 2
    assert "OPENAI_API_KEY" in out
