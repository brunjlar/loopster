from loopster.cli import colorize_unified_diff


def test_colorize_unified_diff_applies_colors():
    diff = (
        '--- a/orig\n'
        '+++ b/new\n'
        '@@ -1,2 +1,2 @@\n'
        ' line one\n'
        '-old\n'
        '+new\n'
    )
    colored = colorize_unified_diff(diff, True)
    # Expect ANSI codes for headers, hunk, minus and plus lines
    assert '\x1b[35m--- a/orig\x1b[0m' in colored
    assert '\x1b[35m+++ b/new\x1b[0m' in colored
    assert '\x1b[36m@@ -1,2 +1,2 @@\x1b[0m' in colored
    assert '\x1b[31m-old\x1b[0m' in colored
    assert '\x1b[32m+new\x1b[0m' in colored


def test_colorize_unified_diff_no_color_when_disabled():
    diff = '--- a\n+++ b\n+add\n-old\n'
    assert colorize_unified_diff(diff, False) == diff

