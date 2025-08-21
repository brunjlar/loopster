import pytest


def test_analyzer_with_fake_llm():
    # Import here to make the failure obvious if dependencies are missing
    from langchain_core.language_models.fake import FakeListLLM
    from loopster.llm.analyzer import Analyzer

    fake = FakeListLLM(responses=["NEW CONFIG CONTENT"])
    a = Analyzer(llm=fake)

    log_text = (
        "[loopster] capturing: codex --help\n"
        "User struggled with tool selection and context window errors.\n"
    )
    cfg_text = (
        "# AGENTS.md\n\n"
        "System prompt with defaults and no retry guidance.\n"
    )

    out = a.analyze_text(log_text=log_text, config_text=cfg_text, output_format="text")
    assert out.strip() == "NEW CONFIG CONTENT"

