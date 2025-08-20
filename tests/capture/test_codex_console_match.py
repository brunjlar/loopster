from pathlib import Path

from loopster.capture.ansi_clean import sanitize_ansi


def _normalize(text: str) -> list[str]:
    # Normalize by stripping trailing spaces and filtering noisy header/footer lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    filtered: list[str] = []
    for ln in lines:
        # Drop local shell prompt and loopster runner notes if present in console paste
        if ("$ " in ln and " loopster capture" in ln) or ln.startswith("("):
            continue
        if ln.startswith("[loopster]"):
            continue
        # Drop empty token-usage footer noise variations
        if ln.startswith("Token usage:"):
            continue
        filtered.append(ln)
    # Collapse consecutive blank lines for robustness
    collapsed: list[str] = []
    prev_blank = False
    for ln in filtered:
        is_blank = ln == ""
        if is_blank and prev_blank:
            continue
        collapsed.append(ln)
        prev_blank = is_blank
    # Trim leading/trailing blanks
    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()
    return collapsed


def test_codex_raw_sanitizes_like_console_repo_samples():
    root = Path(__file__).resolve().parents[2]
    raw = (root / "codex_raw.txt").read_text(encoding="utf-8")
    console = (root / "codex_console.txt").read_text(encoding="utf-8")
    expected = _normalize(console)
    actual = _normalize(sanitize_ansi(raw))

    # Allow for trailing blank lines differences
    while expected and expected[-1] == "":
        expected.pop()
    while actual and actual[-1] == "":
        actual.pop()

    # Compare line-by-line to highlight specific discrepancies
    assert actual == expected
