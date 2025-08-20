import pytest


def test_summarizer_with_fake_llm():
    # Import here to make the failure obvious if dependencies are missing
    from langchain_core.language_models.fake import FakeListLLM
    from loopster.llm.summarizer import Summarizer

    fake = FakeListLLM(responses=["This is the summary."])
    s = Summarizer(llm=fake)

    log_text = """
    [loopster] capturing: codex --help
    Usage: codex [OPTIONS] COMMAND [ARGS]...
    Ran some commands; made a change; encountered an error; retried.
    """.strip()

    out = s.summarize_text(log_text, output_format="text")
    assert out.strip() == "This is the summary."

