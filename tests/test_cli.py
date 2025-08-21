import io
from contextlib import redirect_stdout

from loopster import __version__
from loopster.cli import main, build_analyze_system_prompt


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


def test_cli_analyze_two_pass_flow_with_stub_client(tmp_path, monkeypatch):
    # Prepare sample log and config files
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("ran commands, saw errors, retried")
    cfg_path.write_text("ORIGINAL CONFIG")

    # Stub client to return two different responses for the two LLM calls
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            if self.calls == 1:
                return "General lessons: be concise. Prefer retries with backoff."
            return "UPDATED CONFIG CONTENT"

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    updated_out = tmp_path / "updated_config.md"
    analysis_out = tmp_path / "analysis.txt"

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--analysis-out", str(analysis_out),
        "--out", str(updated_out),
        "--apply", "--yes",
    ])

    assert code == 0
    # Analysis printed
    assert "General lessons" in out
    # Updated config printed
    assert "UPDATED CONFIG CONTENT" in out
    # Diff shown
    assert "@@" in out or "---" in out
    # Files written
    assert analysis_out.read_text().startswith("General lessons")
    assert updated_out.read_text() == "UPDATED CONFIG CONTENT"
    # Original config applied
    assert cfg_path.read_text() == "UPDATED CONFIG CONTENT"


def test_cli_analyze_apply_yes_writes_file(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("errors occurred; suggest retries and better system prompt")
    cfg_path.write_text("original content")

    # Stub client: analysis then updated config
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            return "be concise" if self.calls == 1 else "NEW CONFIG CONTENT"

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--apply",
        "--yes",
    ])

    assert code == 0
    assert cfg_path.read_text() == "NEW CONFIG CONTENT"
    # Ensure some mention of applying is printed
    assert "applied to" in out.lower()


def test_cli_analyze_apply_uses_updated_config_only(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("any log")
    cfg_path.write_text("original content")

    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            return "ignore me" if self.calls == 1 else "ONLY CONFIG BLOCK"

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--apply",
        "--yes",
    ])

    assert code == 0
    assert cfg_path.read_text() == "ONLY CONFIG BLOCK"


def test_cli_analyze_apply_aborts_without_extractable_config(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("any log")
    cfg_path.write_text("original content")

    class StubClient2:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            return "only" if self.calls == 1 else ""

    import loopster.cli as cli
    stub2 = StubClient2()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub2)

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--apply",
        "--yes",
    ])

    assert code == 0
    assert cfg_path.read_text() == "original content"
    assert "could not extract" in out.lower() or "apply aborted" in out.lower()


def test_cli_analyze_apply_aborts_on_project_specific_paths(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("any log")
    cfg_path.write_text("original content")

    class StubClient3:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            return (
                "some" if self.calls == 1 else "Use /home/user/project/.env and src/app.py"
            )

    stub3 = StubClient3()
    import loopster.cli as cli
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub3)

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--apply",
        "--yes",
    ])

    assert code == 0
    assert cfg_path.read_text() == "original content"
    assert "project-specific" in out.lower() or "unsafe" in out.lower()


def test_cli_analyze_apply_aborts_on_project_specific_urls(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("any log")
    cfg_path.write_text("original content")

    class StubClient4:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            return (
                "first"
                if self.calls == 1
                else "Refer to https://example.com/internal-docs for details."
            )

    stub4 = StubClient4()
    import loopster.cli as cli
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub4)

    code, out = run_cli([
        "analyze",
        "--log", str(log_path),
        "--config", str(cfg_path),
        "--model", "fake:analyzer",
        "--apply",
        "--yes",
    ])

    assert code == 0
    assert cfg_path.read_text() == "original content"
    assert "project-specific" in out.lower() or "unsafe" in out.lower()


def test_build_analyze_system_prompt_mentions_project_agnostic():
    p = build_analyze_system_prompt()
    s = p.lower()
    assert "project-agnostic" in s
    assert "avoid project-specific" in s
    assert "global" in s
def test_cli_analyze_no_change_short_circuit(tmp_path, monkeypatch):
    log_path = tmp_path / "session.log"
    cfg_path = tmp_path / "AGENTS.md"
    log_path.write_text("looks fine")
    cfg_path.write_text("ORIGINAL")

    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            # First call (analysis) says NO-CHANGE; there should be no second call
            return "Decision: NO-CHANGE\nBehavior aligns with config."

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    code, out = run_cli([
        "analyze", "--log", str(log_path), "--config", str(cfg_path), "--model", "fake:analyzer"
    ])
    assert code == 0
    assert "Decision: NO-CHANGE" in out
    assert "Diff: (no changes)" in out
