from __future__ import annotations

import re
from typing import List


# General CSI matcher. Allow private parameter bytes '<', '>', and '=' in addition
# to digits, ';' and '?'.
_CSI_RE = re.compile(
    r"\x1B\[[0-9;?<>=]*[ -/]*[@-~]"
)


def _ensure_line(lines: List[List[str]], row: int) -> None:
    while len(lines) <= row:
        lines.append([])


def _ensure_col(lines: List[List[str]], row: int, col: int) -> None:
    _ensure_line(lines, row)
    line = lines[row]
    while len(line) <= col:
        line.append(" ")


def _write_char(lines: List[List[str]], row: int, col: int, ch: str) -> None:
    _ensure_col(lines, row, col)
    # Avoid erasing history: do not overwrite non-space with a space
    if ch == " " and lines[row][col] != " ":
        return
    lines[row][col] = ch


def sanitize_ansi(text: str) -> str:
    """
    Convert ANSI/TUI output into a human-readable text approximation.

    - Handles common control chars: \n, \r, \b, \t
    - Interprets a subset of CSI cursor controls: CUP (H/f), CHA (G), CUF (C), CUB (D),
      CNL (E), CPL (F), EL (K). Styling (SGR m) is removed.
    - Other escape/control sequences are stripped.
    """
    # Quick path: if no ESC present, just normalize newlines
    if "\x1b" not in text:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    # We'll build a simple screen model
    lines: List[List[str]] = [[]]
    # Track carriage-return overwrite intent per line: if a CR occurred, and
    # then fewer characters were written before a newline, truncate the line at
    # the last written column to avoid leftover spinner text.
    cr_active: List[bool] = [False]
    cr_max_cols: List[int] = [0]
    row = 0
    col = 0
    # When TUIs repaint earlier rows (move cursor upward), writes often represent
    # ephemeral UI state (typing echo, spinners). To keep a readable transcript,
    # we suppress printable writes until the next newline when an upward move is
    # detected, rather than attempting to render them at the current row.
    suppress_until_nl = False

    i = 0
    L = len(text)
    while i < L:
        ch = text[i]
        # ESC sequences
        if ch == "\x1b":
            # Skip common 7-bit C1 single-char escapes we see (RI: ESC M, SC: ESC 7, RC: ESC 8)
            if i + 1 < L and text[i + 1] in ("M", "7", "8"):
                i += 2
                continue
            # OSC sequences: ESC ] ... BEL or ESC \
            if i + 1 < L and text[i + 1] == "]":
                # Find BEL or ST terminator
                j = i + 2
                bel = text.find("\x07", j)
                st = text.find("\x1b\\", j)
                if bel == -1 and st == -1:
                    # Unterminated; drop rest
                    break
                if bel == -1:
                    i = st + 2
                    continue
                if st == -1:
                    i = bel + 1
                    continue
                # Take earliest terminator
                i = min(bel + 1, st + 2)
                continue
            # Try to parse CSI
            m = _CSI_RE.match(text, i)
            if m:
                seq = m.group(0)
                final = seq[-1]
                params = seq[2:-1]  # between ESC[ and final
                # Split numeric params
                ps = [p for p in params.split(";") if p]
                def p(n: int, default: int) -> int:
                    try:
                        return int(ps[n]) if n < len(ps) else default
                    except ValueError:
                        return default
                if final in ("m",):
                    # SGR - ignore styling
                    pass
                elif final in ("H", "f"):
                    # CUP: row;col (1-based)
                    r = max(1, p(0, 1)) - 1
                    c = max(1, p(1, 1)) - 1
                    if r < row:
                        # Upward move: suppress ephemeral repaint until newline
                        suppress_until_nl = True
                        # Do not move the logical row to preserve history
                        col = 0
                    else:
                        if r > row:
                            row = r
                        col = c
                        _ensure_col(lines, row, col)
                elif final == "G":
                    # CHA: set column (1-based)
                    c = max(1, p(0, 1)) - 1
                    col = c
                    _ensure_col(lines, row, col)
                elif final == "C":
                    # CUF: forward n columns
                    col += max(1, p(0, 1))
                    _ensure_col(lines, row, col)
                elif final == "D":
                    # CUB: back n columns
                    col = max(0, col - max(1, p(0, 1)))
                elif final == "E":
                    # CNL: next line n, col=0
                    row += max(1, p(0, 1))
                    col = 0
                    # Moving down cancels any suppression from an earlier upward move
                    suppress_until_nl = False
                    _ensure_line(lines, row)
                elif final == "F":
                    # CPL: previous line n, col=0. Treat as an upward move and
                    # suppress subsequent writes until newline to preserve an
                    # append-only transcript.
                    suppress_until_nl = True
                    col = 0
                elif final == "K":
                    # EL (Erase in Line): For transcripts, do not erase history.
                    # Many TUIs clear the current visual line before redrawing; if we
                    # actually truncate here, we lose previously printed content.
                    # Treat as a no-op in the sanitizer so logs remain readable.
                    pass
                elif final == "J":
                    # ED (Erase in Display). TUIs frequently clear the screen before
                    # repainting. Represent this as a frame break: end the current
                    # logical line so subsequent content starts on a fresh line.
                    _ensure_line(lines, row)
                    if lines[row]:
                        row += 1
                        col = 0
                        _ensure_line(lines, row)
                # Ignore other CSI commands
                i = m.end()
                continue
            else:
                # Unknown escape sequence: skip ESC and continue
                i += 1
                continue

        # Control characters
        if ch == "\n":
            # Ensure tracking arrays are large enough for current row
            while len(cr_active) <= row:
                cr_active.append(False)
                cr_max_cols.append(0)
            # If we had a CR on this line, truncate to last written col
            if cr_active[row]:
                # Ensure list exists
                _ensure_line(lines, row)
                # Only truncate if we actually overwrote characters after CR.
                # If no characters were written post-CR before the newline,
                # preserve the original line content.
                maxc = cr_max_cols[row]
                if maxc > 0:
                    lines[row] = lines[row][:maxc]
                cr_active[row] = False
                cr_max_cols[row] = 0
            row += 1
            col = 0
            suppress_until_nl = False
            # Ensure tracking arrays large enough
            _ensure_line(lines, row)
            while len(cr_active) <= row:
                cr_active.append(False)
                cr_max_cols.append(0)
            i += 1
            continue
        if ch == "\r":
            col = 0
            # Mark this line as subject to overwrite truncation
            while len(cr_active) <= row:
                cr_active.append(False)
                cr_max_cols.append(0)
            cr_active[row] = True
            cr_max_cols[row] = 0
            i += 1
            continue
        if ch == "\b":
            col = max(0, col - 1)
            i += 1
            continue
        if ch == "\t":
            # Advance to next tab stop (8 columns)
            next_stop = ((col // 8) + 1) * 8
            while col < next_stop:
                _write_char(lines, row, col, " ")
                col += 1
            i += 1
            continue

        # C0 controls we ignore (except those handled above)
        if "\x00" <= ch <= "\x1f":
            i += 1
            continue

        # Printable
        if not suppress_until_nl:
            _write_char(lines, row, col, ch)
            # Track width written since last CR for truncation logic
            if row < len(cr_active) and cr_active[row]:
                cval = col + 1
                if cval > cr_max_cols[row]:
                    cr_max_cols[row] = cval
            col += 1
        i += 1

    # Finalize any pending CR-overwrite truncation at end-of-stream: if a line
    # saw a CR but no following newline, trim it to the max columns written
    # since that CR so leftover spinner/progress text does not remain.
    for r, active in enumerate(cr_active):
        if active:
            _ensure_line(lines, r)
            maxc = cr_max_cols[r] if r < len(cr_max_cols) else 0
            if maxc and r < len(lines):
                lines[r] = lines[r][:maxc]

    # Join lines, trimming trailing spaces but preserving deliberate gaps
    return "\n".join("".join(line).rstrip() for line in lines)


__all__ = ["sanitize_ansi"]
