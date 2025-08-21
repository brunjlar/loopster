from __future__ import annotations

import argparse
import sys
from .llm import LLMClient
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loopster",
        description="Capture, analyze, and summarize AI assistant CLI sessions.",
    )
    parser.add_argument(
        "--version", action="store_true", help="Print version and exit"
    )

    subparsers = parser.add_subparsers(dest="command")

    # run: capture → summarize → analyze
    run_p = subparsers.add_parser(
        "run",
        help="Capture → summarize → analyze in one go",
        description=(
            "Run a command, save a cleaned log, summarize it, then analyze it against your global config.\n"
            "Uses a single model for both summary and analysis."
        ),
    )
    # capture args
    run_p.add_argument("--cmd", type=str, default=None, help="Command to run")
    run_p.add_argument("--log-out", type=str, default=None, help="Path to save the session log")
    run_p.add_argument("--raw", type=str, default=None, help="Optional path to save raw log")
    run_p.add_argument("--timeout", type=float, default=None, help="Timeout in seconds")
    run_p.add_argument("--no-mirror", action="store_true", help="Do not mirror child output")
    run_p.add_argument("--include-invocation", action="store_true", help="Prepend banner + invocation to the log")
    # model and outputs
    run_p.add_argument("--model", type=str, default=None)
    run_p.add_argument("--summary-out", type=str, default=None, help="Path to save summary output")
    run_p.add_argument("--summary-format", type=str, choices=["markdown", "text", "json"], default="text")
    # analyze args
    run_p.add_argument("--config", type=str, required=False, help="Path to global config (AGENTS.md)")
    run_p.add_argument("--analysis-out", type=str, default=None, help="Path to save analysis text")
    run_p.add_argument("--updated-out", type=str, default=None, help="Path to save updated config proposal")
    run_p.add_argument("--apply", action="store_true", help="Apply improved config to --config")
    run_p.add_argument("--yes", action="store_true", help="Do not prompt when using --apply")
    run_p.add_argument("--no-color", action="store_true", help="Disable ANSI colors in output")

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
    an_p.add_argument("--config", type=str, required=False)
    an_p.add_argument("--analysis-out", type=str, default=None)
    an_p.add_argument("--out", type=str, default=None)
    an_p.add_argument("--model", type=str, default=None)
    an_p.add_argument("--apply", action="store_true", help="Apply improved config to --config")
    an_p.add_argument("--yes", action="store_true", help="Do not prompt when using --apply")
    an_p.add_argument("--no-color", action="store_true", help="Disable ANSI colors in output")

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


def build_analyze_system_prompt() -> str:
    return (
        "You are Loopster, a CLI assistant configuration analyst.\n"
        "Goal: Assess a session LOG against the GLOBAL, project-agnostic CONFIG.\n"
        "Derive only those general lessons that reveal significant gaps between behavior and the config.\n"
        "Also surface any INDEPENDENT CRITICAL FAILURES observed in the LOG even if not covered by CONFIG.\n\n"
        "Constraints:\n"
        "- Focus on durable, project-agnostic guidance (policies, reasoning steps,\n"
        "  safety, clarification strategies, retry policy, uncertainty handling).\n"
        "- Avoid project-specific details (paths, filenames, API schemas, repo structure,\n"
        "  proper nouns, domain-only facts).\n"
        "- Do not include secrets or copy raw project content.\n"
        "- Use placeholders where needed (e.g., <PROJECT>, <API_KEY>).\n"
        "- Prefer concise, high-signal directives.\n"
        "- Bias toward failures and friction points over praise.\n"
        "- Only include issues that warrant a global config change; if none, say so clearly.\n"
        "- Prioritize at most 3–5 broadly useful issues; omit minor nitpicks.\n\n"
        "Method:\n"
        "A) Config Compliance: Compare LOG vs CONFIG. For each alleged issue: provide a short quote from LOG as evidence\n"
        "   and cite the CONFIG direction it conflicts with; assign severity (critical/major/minor). Retain severity ≥ major.\n"
        "B) Independent Critical Failures: If the LOG shows severe breakdowns not covered by CONFIG (e.g., infinite/repeated loops,\n"
        "   unbounded retries without learning, ignoring explicit user direction, unsafe actions, privacy leaks), list them with evidence\n"
        "   and severity. Retain only severity ≥ major.\n\n"
        "Output: Start with a single line 'Decision: CHANGE' or 'Decision: NO-CHANGE'.\n"
        "- Decision: CHANGE if (A) any config compliance issues severity ≥ major OR (B) any independent critical failures severity ≥ major.\n"
        "- If NO-CHANGE: add one short sentence why (e.g., 'Behavior aligns with config; no significant gaps').\n"
        "- If CHANGE: list 1–3 general lessons with evidence quotes; keep it project-agnostic.\n"
        "Do not return JSON; do not add code fences."
    )


def get_llm_client() -> LLMClient:
    return LLMClient()


def _select_model_or_error(cmd_label: str, model: str | None) -> tuple[str | None, str | None]:
    """Infer provider from model and check required API keys.

    Returns (model, error_message). On success, error_message is None.
    """
    import os
    from .llm.model_factory import infer_provider_from_model

    selected = model or os.environ.get("LOOPSTER_MODEL") or "gpt-5"
    provider = infer_provider_from_model(selected)

    def _require_env(var: str, provider_label: str) -> bool:
        if os.environ.get(var):
            return True
        print(
            f"[loopster] {cmd_label}: missing API key for {provider_label}. Set {var} in your environment."
        )
        return False

    prov_l = (provider or "").lower()
    if prov_l in {"openai", "chatgpt", "gpt"}:
        if not _require_env("OPENAI_API_KEY", "OpenAI"):
            return None, "missing OPENAI_API_KEY"
    elif prov_l in {"google", "gemini"}:
        if not _require_env("GOOGLE_API_KEY", "Google Gemini"):
            return None, "missing GOOGLE_API_KEY"
    elif prov_l == "fake":
        pass
    else:
        print(f"[loopster] {cmd_label}: could not infer provider from model: {selected}")
        return None, "could not infer provider"
    return selected, None


def colorize_unified_diff(diff_text: str, enable: bool) -> str:
    if not enable or not diff_text:
        return diff_text
    out_lines: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith('+++ ') or line.startswith('--- '):
            out_lines.append(f"\033[35m{line.rstrip()}\033[0m\n")  # magenta
        elif line.startswith('@@'):
            out_lines.append(f"\033[36m{line.rstrip()}\033[0m\n")  # cyan
        elif line.startswith('+') and not line.startswith('+++'):
            out_lines.append(f"\033[32m{line.rstrip()}\033[0m\n")  # green
        elif line.startswith('-') and not line.startswith('---'):
            out_lines.append(f"\033[31m{line.rstrip()}\033[0m\n")  # red
        elif line.startswith(' '):
            out_lines.append(f"\033[2m{line.rstrip()}\033[0m\n")  # dim
        else:
            out_lines.append(line)
    return ''.join(out_lines)


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
        # Validate required inputs
        if not getattr(args, "cmd", None):
            print("[loopster] run: provide --cmd to run (no-op)")
            return 0
        # Select model and validate API keys
        model, err = _select_model_or_error("run", getattr(args, "model", None))
        if err:
            return 2
        # Prepare capture
        from .capture.pipe_capture import capture_command
        from pathlib import Path
        import tempfile

        auto_log = False
        if getattr(args, "log_out", None):
            log_path = args.log_out
        else:
            fd, path = tempfile.mkstemp(prefix="loopster_run_", suffix=".log")
            os.close(fd)
            log_path = path
            auto_log = True

        print(f"[loopster] run: capturing → {args.cmd}\n[loopster] log: {log_path}")
        header: str | None = None
        if getattr(args, "include_invocation", False):
            # build banner and invocation
            parts = ["loopster", "run", "--cmd", args.cmd]
            if getattr(args, "log_out", None):
                parts += ["--log-out", log_path]
            if getattr(args, "raw", None):
                parts += ["--raw", args.raw]
            if getattr(args, "timeout", None) is not None:
                parts += ["--timeout", str(args.timeout)]
            if getattr(args, "no_mirror", False):
                parts += ["--no-mirror"]
            parts += ["--include-invocation"]
            header = " ".join(parts) + "\n" + f"[loopster] run: capturing → {args.cmd}\n[loopster] log: {log_path}\n"

        child_code = capture_command(
            args.cmd,
            log_path,
            timeout=getattr(args, "timeout", None),
            mirror_to_stdout=not getattr(args, "no_mirror", False),
            raw_output_path=getattr(args, "raw", None),
            prepend_header=header,
        )
        if auto_log:
            print(f"[loopster] session saved to: {log_path}")
        print(f"[loopster] child exit code: {child_code}")

        # Summarize
        try:
            client = get_llm_client()
            sum_system = (
                "You are Loopster, a CLI session summarizer.\n"
                "Summarize the session log succinctly. Focus on:\n"
                "- Commands executed and their intent\n"
                "- Notable outputs, errors, and retries\n"
                "- Configuration changes or suggestions\n"
                f"Write the summary in {getattr(args, 'summary_format', 'text')} format."
            )
            sum_text = client.ask(
                system_prompt=sum_system,
                prompt="Session log follows. Provide a concise summary.",
                files=[Path(log_path)],
                model=model,
            )
        except Exception as e:
            print(f"[loopster] run: LLM error during summary: {e}")
            return 2
        if getattr(args, "summary_out", None):
            try:
                Path(args.summary_out).write_text(sum_text, encoding="utf-8")
                print(f"[loopster] summary saved → {args.summary_out}")
            except Exception as e:
                print(f"[loopster] run: failed to write summary: {e}")
                return 2
        else:
            print("\n[loopster] Summary:\n" + sum_text)

        # Analyze (reuse analyze path, but with our model)
        if not getattr(args, "config", None):
            print("[loopster] run: no --config provided; skipping analysis.")
            return 0
        # Read inputs
        try:
            cfg_text = Path(args.config).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[loopster] run: failed to read config: {e}")
            return 2

        # Pass 1: analysis
        try:
            analysis_text = client.ask(
                system_prompt=build_analyze_system_prompt(),
                prompt=(
                    "Compare LOG vs CONFIG; also check for independent critical failures not covered by CONFIG. "
                    "Start with 'Decision: NO-CHANGE' if no severity ≥ major gaps/failures; otherwise 'Decision: CHANGE' and list 1–3 major lessons with evidence."
                ),
                files=[Path(log_path), Path(args.config)],
                model=model,
            )
        except Exception as e:
            print(f"[loopster] run: LLM error during analysis: {e}")
            return 2

        # Colored printing helpers (reuse analyze behavior)
        def _use_color() -> bool:
            if getattr(args, "no_color", False):
                return False
            if os.environ.get("NO_COLOR"):
                return False
            return sys.stdout.isatty()
        def _c(text: str, code: str) -> str:
            return f"\033[{code}m{text}\033[0m" if _use_color() else text

        print(_c("[loopster] Analysis (general lessons):", "33"))
        print()
        print(analysis_text)
        if getattr(args, "analysis_out", None):
            try:
                Path(args.analysis_out).write_text(analysis_text, encoding="utf-8")
                print(f"[loopster] analysis saved → {args.analysis_out}")
            except Exception as e:
                print(f"[loopster] run: failed to write analysis: {e}")
                return 2

        # Decision gate
        decision_line = analysis_text.splitlines()[0].strip().lower() if analysis_text.strip() else ""
        no_change = decision_line.startswith("decision:") and ("no-change" in decision_line)

        # Pass 2: updated config
        if no_change:
            updated_config = cfg_text
        else:
            try:
                updated_config = client.ask(
                    system_prompt=(
                        "You are Loopster, a careful editor of a global, project-agnostic system prompt.\n"
                        "Goal: Apply the provided general lessons to improve the config WITHOUT overwriting the user's intent.\n"
                        "Prefer MINIMAL, SURGICAL edits. Preserve structure; avoid project specifics.\n"
                        "If the analysis indicates no significant issues, return the ORIGINAL config UNCHANGED.\n"
                        "Output only the complete updated config (no extra commentary, no fences)."
                    ),
                    prompt=(
                        "Apply the analysis below to the following config. Return only the updated config.\n\n=== ANALYSIS ===\n"
                        + analysis_text
                    ),
                    files=[Path(args.config)],
                    model=model,
                )
            except Exception as e:
                print(f"[loopster] run: LLM error during config update: {e}")
                return 2

        print(_c("\n[loopster] Updated Config:", "33"))
        print()
        print(updated_config)

        # Diff
        import difflib
        orig_lines = cfg_text.splitlines(keepends=True)
        new_lines = updated_config.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            new_lines,
            fromfile=str(args.config) + " (original)",
            tofile=str(args.config) + " (updated)",
        )
        diff_text = "".join(diff)
        if diff_text.strip():
            print(_c("\n[loopster] Diff:", "33"))
            print()
            print(colorize_unified_diff(diff_text, _use_color()))
        else:
            print(_c("\n[loopster] Diff: (no changes)", "33"))

        # Save updated proposal
        if getattr(args, "updated_out", None):
            try:
                Path(args.updated_out).write_text(updated_config, encoding="utf-8")
                print(f"[loopster] updated config saved → {args.updated_out}")
            except Exception as e:
                print(f"[loopster] run: failed to write updated config: {e}")
                return 2

        # Optional apply (reuse checks from analyze)
        if getattr(args, "apply", False):
            def _contains_project_specific(text: str) -> bool:
                import re
                patterns = [
                    r"https?://\S+",
                    r"\b(?:git@|github\.com|gitlab\.com|bitbucket\.org)\b",
                    r"(^|\s)/[^\s]+",
                    r"[A-Za-z]:\\\\",
                    r"\b\w+\.(?:py|js|ts|md|json|yaml|yml|toml|ini|env|sh|txt)\b",
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                ]
                for pat in patterns:
                    if re.search(pat, text, re.IGNORECASE | re.MULTILINE):
                        return True
                return False
            if _contains_project_specific(updated_config):
                print(
                    "[loopster] run: detected project-specific details in the proposed config; apply aborted to protect your global settings."
                )
                return 0
            if not getattr(args, "yes", False):
                try:
                    resp = input(f"Apply changes to {args.config}? [y/N]: ").strip().lower()
                except Exception:
                    resp = ""
                if resp not in {"y", "yes"}:
                    print("[loopster] apply aborted.")
                    return 0
            try:
                Path(args.config).write_text(updated_config, encoding="utf-8")
            except Exception as e:
                print(f"[loopster] run: failed to apply config: {e}")
                return 2
            print(f"[loopster] analysis applied to {args.config}")
        return 0
    if args.command == "capture":
        # Lazy import to keep CLI fast
        from .capture.pipe_capture import capture_command
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
        # Require both log and config; otherwise no-op to match summarize UX
        log_path = getattr(args, "log", None)
        cfg_path = getattr(args, "config", None)
        if not log_path or not cfg_path:
            print("[loopster] analyze: provide --log and --config (no-op)")
            return 0
        from pathlib import Path
        try:
            log_text = Path(log_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[loopster] analyze: failed to read log: {e}")
            return 2
        try:
            cfg_text = Path(cfg_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[loopster] analyze: failed to read config: {e}")
            return 2

        # Build model selection purely from CLI/env
        from .llm import LLMClient
        from .llm.model_factory import infer_provider_from_model

        model = getattr(args, "model", None) or os.environ.get("LOOPSTER_MODEL") or "gpt-5"
        provider = infer_provider_from_model(model)

        # Helpful API key checks
        def _require_env(var: str, provider_label: str) -> bool:
            if os.environ.get(var):
                return True
            print(
                f"[loopster] analyze: missing API key for {provider_label}. "
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
            pass
        else:
            print(f"[loopster] analyze: could not infer provider from model: {model}")
            return 2

        # Pass 1: analysis of the session log to extract general lessons
        analysis_prompt = (
            "Compare LOG vs CONFIG; also check for independent critical failures not covered by CONFIG. "
            "Start with 'Decision: NO-CHANGE' if no severity ≥ major gaps/failures; otherwise 'Decision: CHANGE' and list 1–3 major lessons with evidence."
        )
        try:
            client = get_llm_client()
            analysis_text = client.ask(
                system_prompt=build_analyze_system_prompt(),
                prompt=analysis_prompt,
                files=[Path(log_path), Path(cfg_path)],
                model=model,
            )
        except Exception as e:
            print(f"[loopster] analyze: LLM error during analysis: {e}")
            return 2

        # Colored section headers
        def _use_color() -> bool:
            if getattr(args, "no_color", False):
                return False
            if os.environ.get("NO_COLOR"):
                return False
            return sys.stdout.isatty()
        def _c(text: str, code: str) -> str:
            return f"\033[{code}m{text}\033[0m" if _use_color() else text

        print(_c("[loopster] Analysis (general lessons):", "33"))  # yellow
        print()
        print(analysis_text)
        analysis_out = getattr(args, "analysis_out", None)
        if analysis_out:
            try:
                Path(analysis_out).write_text(analysis_text, encoding="utf-8")
            except Exception as e:
                print(f"[loopster] analyze: failed to write analysis: {e}")
                return 2
            print(f"[loopster] analysis saved → {analysis_out}")

        # If analysis recommends NO-CHANGE, keep config verbatim and show no-op diff
        decision_line = analysis_text.splitlines()[0].strip().lower() if analysis_text.strip() else ""
        no_change = decision_line.startswith("decision:") and ("no-change" in decision_line)

        # Pass 2: update the config based on the analysis while preserving intent
        update_system = (
            "You are Loopster, a careful editor of a global, project-agnostic system prompt.\n"
            "Goal: Apply the provided general lessons to improve the config WITHOUT "
            "overwriting the user's original intent. Prefer MINIMAL, SURGICAL edits.\n"
            "Preserve existing sections and wording where possible; add concise, durable, "
            "project-agnostic directives. Avoid project-specific details.\n"
            "Only make drastic changes when the analysis indicates severe, systemic failure.\n"
            "If the analysis indicates no significant issues, return the ORIGINAL config \n"
            "UNCHANGED (verbatim). Otherwise, limit changes to the smallest set necessary.\n"
            "Output only the complete updated config (no extra commentary, no fences)."
        )
        if no_change:
            updated_config = cfg_text
        else:
            try:
                updated_config = client.ask(
                    system_prompt=update_system,
                    prompt=(
                        "Apply the analysis below to the following config. Return only the "
                        "updated config.\n\n=== ANALYSIS ===\n" + analysis_text
                    ),
                    files=[Path(cfg_path)],
                    model=model,
                )
            except Exception as e:
                print(f"[loopster] analyze: LLM error during config update: {e}")
                return 2

        print(_c("\n[loopster] Updated Config:", "33"))  # yellow
        print()
        print(updated_config)

        # Show a unified diff for visibility
        try:
            import difflib
            orig_lines = cfg_text.splitlines(keepends=True)
            new_lines = updated_config.splitlines(keepends=True)
            diff = difflib.unified_diff(
                orig_lines,
                new_lines,
                fromfile=str(cfg_path) + " (original)",
                tofile=str(cfg_path) + " (updated)",
            )
            diff_text = "".join(diff)
            if diff_text.strip():
                print(_c("\n[loopster] Diff:", "33"))  # yellow
                print()
                print(colorize_unified_diff(diff_text, _use_color()))
            else:
                print(_c("\n[loopster] Diff: (no changes)", "33"))
        except Exception:
            pass

        # Save updated config to --out if provided
        out_path = getattr(args, "out", None)
        if out_path:
            try:
                Path(out_path).write_text(updated_config, encoding="utf-8")
            except Exception as e:
                print(f"[loopster] analyze: failed to write updated config: {e}")
                return 2
            print(f"[loopster] updated config saved → {out_path}")

        # Optionally apply the improved config to the provided --config path
        if getattr(args, "apply", False):
            def _extract_config_block(text: str) -> str | None:
                # In two-pass flow, the updated config is already plain text
                return text if text.strip() else None
            def _contains_project_specific(text: str) -> bool:
                import re
                patterns = [
                    r"https?://\S+",  # URLs
                    r"\b(?:git@|github\.com|gitlab\.com|bitbucket\.org)\b",  # git hosts
                    r"(^|\s)/[^\s]+",  # absolute unix path
                    r"[A-Za-z]:\\\\",  # windows drive path
                    r"\b\w+\.(?:py|js|ts|md|json|yaml|yml|toml|ini|env|sh|txt)\b",  # filenames
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",  # emails
                ]
                for pat in patterns:
                    if re.search(pat, text, re.IGNORECASE | re.MULTILINE):
                        return True
                return False

            new_cfg = _extract_config_block(updated_config)
            # Confirm unless --yes
            if not getattr(args, "yes", False):
                print(
                    f"[loopster] about to apply improved config to {cfg_path}. "
                    "Re-run with --yes to confirm non-interactively."
                )
                try:
                    resp = input("Apply changes? [y/N]: ").strip().lower()
                except Exception:
                    resp = ""
                if resp not in {"y", "yes"}:
                    print("[loopster] apply aborted.")
                    return 0
            if new_cfg is None:
                print("[loopster] analyze: could not extract an updated config block; apply aborted.")
                return 0
            if _contains_project_specific(new_cfg):
                print(
                    "[loopster] analyze: detected project-specific details in the proposed config; "
                    "apply aborted to protect your global settings."
                )
                return 0
            try:
                Path(cfg_path).write_text(new_cfg, encoding="utf-8")
            except Exception as e:
                print(f"[loopster] analyze: failed to apply config: {e}")
                return 2
            print(f"[loopster] analysis applied to {cfg_path}")
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
        from .llm import LLMClient
        from .llm.model_factory import infer_provider_from_model

        model = getattr(args, "model", None) or os.environ.get("LOOPSTER_MODEL") or "gpt-5"
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
