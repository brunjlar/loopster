from loopster.llm.analyzer import build_analyzer_instructions


def test_analyzer_instructions_are_project_agnostic():
    text = build_analyzer_instructions()
    # Ensure guidance about general, project-agnostic config improvements
    assert "project-agnostic" in text.lower()
    assert "global" in text.lower()
    assert "avoid project-specific" in text.lower()
    # Ensure JSON contract is specified
    assert "json" in text.lower()
    assert "updated_config" in text
