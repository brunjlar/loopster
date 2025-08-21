import io
from contextlib import redirect_stdout


def run_cli(args):
    from loopster.cli import main

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_run_pipeline_no_change(tmp_path, monkeypatch):
    # Stub capture to write a simple log
    log_written = tmp_path / "session.log"

    def stub_capture(cmd, out_path, timeout=None, mirror_to_stdout=True, raw_output_path=None, prepend_header=None):
        p = tmp_path / "actual.log"
        p.write_text("LOG CONTENT")
        # run() passes path from args; write to that path
        from pathlib import Path
        Path(out_path).write_text("LOG CONTENT")
        return 0

    import loopster.capture.pipe_capture as pc
    monkeypatch.setattr(pc, "capture_command", stub_capture)

    # Stub LLM client: summary then analysis("NO-CHANGE"); no update call expected
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            if self.calls == 1:
                return "SUMMARY TEXT"
            return "Decision: NO-CHANGE\nBehavior aligns with config."

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    cfg_path = tmp_path / "AGENTS.md"
    cfg_path.write_text("ORIGINAL CFG")
    summary_out = tmp_path / "summary.txt"
    analysis_out = tmp_path / "analysis.txt"
    updated_out = tmp_path / "updated.md"

    code, out = run_cli([
        "run",
        "--cmd", "echo hi",
        "--config", str(cfg_path),
        "--model", "fake:run",
        "--summary-out", str(summary_out),
        "--analysis-out", str(analysis_out),
        "--updated-out", str(updated_out),
        "--no-color",
    ])

    assert code == 0
    # Summary saved (printed header omitted when saving to file)
    assert summary_out.read_text() == "SUMMARY TEXT"
    assert "summary saved" in out.lower()
    # Analysis saved and starts with decision line
    assert analysis_out.read_text().startswith("Decision: NO-CHANGE")
    assert "Decision: NO-CHANGE" in out
    # Updated config equals original; diff shows no changes
    assert updated_out.read_text() == "ORIGINAL CFG"
    assert "Diff: (no changes)" in out
    # Only two LLM calls (summary + analysis)
    assert stub.calls == 2


def test_run_pipeline_apply_change(tmp_path, monkeypatch):
    # Stub capture
    def stub_capture(cmd, out_path, timeout=None, mirror_to_stdout=True, raw_output_path=None, prepend_header=None):
        from pathlib import Path
        Path(out_path).write_text("LOG CONTENT")
        return 0

    import loopster.capture.pipe_capture as pc
    monkeypatch.setattr(pc, "capture_command", stub_capture)

    # Stub LLM client: summary, analysis change, update config
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            if self.calls == 1:
                return "SUMMARY"
            if self.calls == 2:
                return "Decision: CHANGE\nMajor gap example with evidence."
            return "NEW CFG"

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    cfg_path = tmp_path / "AGENTS.md"
    cfg_path.write_text("ORIG")
    updated_out = tmp_path / "updated.md"

    code, out = run_cli([
        "run",
        "--cmd", "echo hi",
        "--config", str(cfg_path),
        "--model", "fake:run",
        "--updated-out", str(updated_out),
        "--apply", "--yes",
        "--no-color",
    ])

    assert code == 0
    # Config applied and file overwritten
    assert cfg_path.read_text() == "NEW CFG"
    assert updated_out.read_text() == "NEW CFG"
    assert "analysis applied to" in out.lower()
    # Expect a non-empty diff in output
    assert "@@" in out or "---" in out


def test_run_prints_summary_when_not_saving(tmp_path, monkeypatch):
    # Stub capture
    def stub_capture(cmd, out_path, timeout=None, mirror_to_stdout=True, raw_output_path=None, prepend_header=None):
        from pathlib import Path
        Path(out_path).write_text("LOG CONTENT")
        return 0

    import loopster.capture.pipe_capture as pc
    monkeypatch.setattr(pc, "capture_command", stub_capture)

    # Stub LLM: summary then NO-CHANGE
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            if self.calls == 1:
                return "SUMMARY BODY"
            return "Decision: NO-CHANGE\nAll good."

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    cfg_path = tmp_path / "AGENTS.md"
    cfg_path.write_text("ORIG CFG")

    code, out = run_cli([
        "run",
        "--cmd", "echo hi",
        "--config", str(cfg_path),
        "--model", "fake:run",
        "--no-color",
    ])

    assert code == 0
    assert "Summary:" in out
    assert "SUMMARY BODY" in out
    assert "Decision: NO-CHANGE" in out
    assert "Diff: (no changes)" in out


def test_run_apply_aborts_on_project_specific_updated_config(tmp_path, monkeypatch):
    # Stub capture
    def stub_capture(cmd, out_path, timeout=None, mirror_to_stdout=True, raw_output_path=None, prepend_header=None):
        from pathlib import Path
        Path(out_path).write_text("LOG CONTENT")
        return 0

    import loopster.capture.pipe_capture as pc
    monkeypatch.setattr(pc, "capture_command", stub_capture)

    # Stub LLM: summary, analysis change, updated config contains absolute path
    class StubClient:
        def __init__(self):
            self.calls = 0
        def ask(self, *, system_prompt, prompt=None, files=None, model=None):
            self.calls += 1
            if self.calls == 1:
                return "SUMMARY"
            if self.calls == 2:
                return "Decision: CHANGE\nMajor: tweak policy."
            return "Use /home/user/project/.env and keep reports in reports.md"

    import loopster.cli as cli
    stub = StubClient()
    monkeypatch.setattr(cli, "get_llm_client", lambda: stub)

    cfg_path = tmp_path / "AGENTS.md"
    cfg_path.write_text("ORIG")
    updated_out = tmp_path / "updated.md"

    code, out = run_cli([
        "run",
        "--cmd", "echo hi",
        "--config", str(cfg_path),
        "--model", "fake:run",
        "--updated-out", str(updated_out),
        "--apply", "--yes",
        "--no-color",
    ])

    assert code == 0
    # Apply aborted; file unchanged
    assert cfg_path.read_text() == "ORIG"
    # But updated proposal was saved
    assert updated_out.read_text().startswith("Use /home/user/project/.env")
    assert "detected project-specific details" in out.lower()
