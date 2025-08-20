import io
from pathlib import Path


def test_client_with_fake_llm_text_only(tmp_path):
    # Import locally to surface missing deps clearly
    from langchain_core.language_models.fake import FakeListLLM
    from loopster.llm.client import LLMClient

    fake = FakeListLLM(responses=["OK"])
    client = LLMClient(llm=fake)

    out = client.ask(system_prompt="You are helpful.", prompt="Say hi")
    assert out == "OK"


def test_client_with_fake_llm_and_files(tmp_path):
    from langchain_core.language_models.fake import FakeListLLM
    from loopster.llm.client import LLMClient

    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("alpha")
    f2.write_text("beta")

    fake = FakeListLLM(responses=["FILES INCLUDED"])
    client = LLMClient(llm=fake)

    out = client.ask(
        system_prompt="Summarize files.",
        prompt="Combine: ",
        files=[f1, f2],
    )
    assert out == "FILES INCLUDED"


def test_client_unsupported_provider_errors():
    from loopster.llm.client import LLMClient

    client = LLMClient(provider="unknown", model="x")
    try:
        client.ask(system_prompt="x", prompt="y")
        raise AssertionError("Expected ValueError for unsupported provider")
    except ValueError as e:
        assert "Unsupported provider" in str(e)

