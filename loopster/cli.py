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
    sum_p.add_argument("--model", type=str, default=None)

    # models listing
    models_p = subparsers.add_parser("models", help="List supported model names")

    # (config subcommand removed)

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

        # Build model selection purely from CLI/env
        import os
        from .llm import LLMClient
        from .llm.model_factory import infer_provider_from_model

        model = getattr(args, "model", None) or os.environ.get("LOOPSTER_MODEL") or "gpt-4o-mini"
        provider = infer_provider_from_model(model)

        # Helpful API key checks
        def _require_env(var: str, provider_label: str) -> bool:
            if os.environ.get(var):
                return True
            print(
                f"[loopster] summarize: missing API key for {provider_label}. "
                f"Set {var} in your environment."
            )
            return False

        prov_l = (provider or "").lower()
        if prov_l in {"openai", "chatgpt", "gpt"}:
            if not _require_env("OPENAI_API_KEY", "OpenAI"):
                return 2
        elif prov_l in {"google", "gemini"}:
            if not _require_env("GOOGLE_API_KEY", "Google Gemini"):
                return 2
        elif prov_l == "fake":
            pass  # no key required
        else:
            print(f"[loopster] summarize: could not infer provider from model: {model}")
            return 2

        # Use LLMClient
        system_prompt = (
            "You are Loopster, a CLI session summarizer.\n"
            "Summarize the session log succinctly. Focus on:\n"
            "- Commands executed and their intent\n"
            "- Notable outputs, errors, and retries\n"
            "- Configuration changes or suggestions\n"
            "Write the summary in {format} format."
        ).format(format=getattr(args, "format", "text"))

        user_prompt = "Session log follows. Provide a concise summary."

        try:
            client = LLMClient()  # use model-only inference path
            out_text = client.ask(system_prompt=system_prompt, prompt=user_prompt, files=[Path(log_path)], model=model)
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
    if args.command == "models":
        from .llm.model_factory import OPENAI_MODELS, GEMINI_MODELS
        print("OpenAI models:")
        for m in OPENAI_MODELS:
            print(f" - {m}")
        print("\nGoogle Gemini models:")
        for m in GEMINI_MODELS:
            print(f" - {m}")
        print("\nTesting/development:")
        print(" - fake:<anything> (prints LOOPSTER_FAKE_RESPONSE or 'OK')")
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
