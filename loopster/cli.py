from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loopster",
        description="Capture, analyze, and summarize AI assistant CLI sessions.",
    )
    parser.add_argument(
        "--version", action="store_true", help="Print version and exit"
    )

    subparsers = parser.add_subparsers(dest="command")

    # run
    run_p = subparsers.add_parser("run", help="Capture → analyze → summarize")
    run_p.add_argument("--config", type=str, default=None)
    run_p.add_argument("--provider", type=str, default=None)
    run_p.add_argument("--tool", type=str, default=None)
    # formerly had --use (auto/pipe/script); removed for simplicity
    run_p.add_argument("--log-dir", type=str, default=None)

    # capture
    cap_p = subparsers.add_parser(
        "capture",
        help="Only capture a session",
        description=(
            "Run a command and save a cleaned, human-readable log.\n"
            "- Removes ANSI/TUI control sequences while preserving layout.\n"
            "- Always writes the partial log on timeout or error.\n"
            "- On timeout, exits with code 124."
        ),
    )
    cap_p.add_argument("--cmd", type=str, default=None, help="Command to run")
    # Support both --output and the common shorthand --out
    cap_p.add_argument("--output", type=str, default=None, help="Log file path")
    cap_p.add_argument("--out", dest="output", type=str, help="Log file path (alias)")
    cap_p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "Timeout in seconds. On timeout, the child is terminated,"
            " the partial cleaned log is saved, and exit code 124 is returned."
        ),
    )
    cap_p.add_argument(
        "--no-mirror",
        action="store_true",
        help="Do not mirror child output to this terminal (useful for noisy TUIs)",
    )
    cap_p.add_argument(
        "--raw",
        type=str,
        default=None,
        help="Optional path to save the raw, uncleaned log (for debugging)",
    )
    cap_p.add_argument(
        "--include-invocation",
        action="store_true",
        help=(
            "Prefix cleaned log with the executed command and loopster banner lines"
        ),
    )

    # analyze
    an_p = subparsers.add_parser("analyze", help="Analyze an existing log")
    an_p.add_argument("--log", type=str, required=False)
    an_p.add_argument("--format", type=str, choices=["json", "text"], default="text")

    # summarize
    sum_p = subparsers.add_parser("summarize", help="Summarize a session log")
    sum_p.add_argument("--log", type=str, required=False)
    sum_p.add_argument(
        "--format", type=str, choices=["markdown", "text", "json"], default="text"
    )
    sum_p.add_argument("--out", type=str, default=None)

    # config
    cfg_p = subparsers.add_parser("config", help="Show/validate effective config")
    cfg_p.add_argument("--show", action="store_true")
    cfg_p.add_argument("--validate", action="store_true")
    cfg_p.add_argument("--set", action="append", default=[])
    cfg_p.add_argument("--save", type=str, default=None)

    # sanitize
    san_p = subparsers.add_parser(
        "sanitize",
        help="Sanitize an existing raw log (ANSI → human-readable)",
        description=(
            "Read a raw log file, strip ANSI control, and write a cleaned output."
        ),
    )
    san_p.add_argument("--raw", type=str, required=True, help="Path to raw log")
    san_p.add_argument("--out", type=str, required=True, help="Path to cleaned log")

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    # Parse args, but convert argparse-triggered exits (e.g., --help) into return codes
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code)

    if args.version:
        try:
            from . import __version__

            print(__version__)
        except Exception:
            print("0.0.0")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    # For initial scaffold, simply acknowledge commands and exit 0
    if args.command == "run":
        print("[loopster] run: capture → analyze → summarize (stub)")
        return 0
    if args.command == "capture":
        # Lazy import to keep CLI fast
        from .capture.pipe_capture import capture_command
        import os
        import tempfile

        if not getattr(args, "cmd", None):
            print("[loopster] capture: provide --cmd to run (no-op)")
            return 0

        auto_output = False
        if args.output:
            output = args.output
        else:
            fd, path = tempfile.mkstemp(prefix="loopster_", suffix=".log")
            os.close(fd)
            output = path
            auto_output = True

        print(f"[loopster] capturing: {args.cmd}\n[loopster] log: {output}")

        header: str | None = None
        if getattr(args, "include_invocation", False):
            # Build an invocation summary and banner
            # Only include flags explicitly provided by the user
            parts = ["loopster", "capture"]
            if args.cmd:
                parts += ["--cmd", args.cmd]
            if args.output:
                parts += ["--out", output]
            if getattr(args, "raw", None):
                parts += ["--raw", args.raw]
            if getattr(args, "timeout", None) is not None:
                parts += ["--timeout", str(args.timeout)]
            if getattr(args, "no_mirror", False):
                parts += ["--no-mirror"]
            parts += ["--include-invocation"]
            cmd_line = " ".join(parts)
            header = cmd_line + "\n" + f"[loopster] capturing: {args.cmd}\n[loopster] log: {output}\n"
        code = capture_command(
            args.cmd,
            output,
            timeout=getattr(args, "timeout", None),
            mirror_to_stdout=not getattr(args, "no_mirror", False),
            raw_output_path=getattr(args, "raw", None),
            prepend_header=header,
        )
        if auto_output:
            print(f"[loopster] session saved to: {output}")
        print(f"[loopster] finished with exit code {code}")
        return code
    if args.command == "analyze":
        print("[loopster] analyze (stub)")
        return 0
    if args.command == "summarize":
        # If no log provided, keep a no-op behavior to not break existing flows
        log_path = getattr(args, "log", None)
        if not log_path:
            print("[loopster] summarize: provide --log to generate a summary (no-op)")
            return 0
        from pathlib import Path
        try:
            log_text = Path(log_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[loopster] summarize: failed to read log: {e}")
            return 2

        # Build summarizer using env-based defaults unless explicitly configured later
        from .llm import Summarizer
        import os

        provider = os.environ.get("LOOPSTER_PROVIDER")
        model = os.environ.get("LOOPSTER_MODEL")
        try:
            if provider and model:
                summarizer = Summarizer(provider=provider, model=model)
            else:
                # Defer model selection to provider defaults; this path will likely error
                # if no env is configured, but we catch and report below.
                summarizer = Summarizer(provider=provider or "openai", model=model or "gpt-4o-mini")
            out_text = summarizer.summarize_text(log_text, output_format=getattr(args, "format", "text"))
        except Exception as e:
            print(f"[loopster] summarize: LLM error: {e}")
            return 2
        out_path = getattr(args, "out", None)
        if out_path:
            try:
                Path(out_path).write_text(out_text, encoding="utf-8")
            except Exception as e:
                print(f"[loopster] summarize: failed to write output: {e}")
                return 2
            print(f"[loopster] summary written → {out_path}")
        else:
            print(out_text)
        return 0
    if args.command == "config":
        print("[loopster] config (stub)")
        return 0
    if args.command == "sanitize":
        from .capture.ansi_clean import sanitize_ansi
        from pathlib import Path

        raw_path = args.raw
        out_path = args.out
        try:
            raw_text = Path(raw_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[loopster] sanitize: failed to read raw log: {e}")
            return 2
        cleaned = sanitize_ansi(raw_text)
        try:
            Path(out_path).write_text(cleaned, encoding="utf-8")
        except Exception as e:
            print(f"[loopster] sanitize: failed to write cleaned log: {e}")
            return 2
        print(f"[loopster] sanitized → {out_path}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
