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
    run_p.add_argument("--use", type=str, choices=["auto", "pty", "script"], default="auto")
    run_p.add_argument("--log-dir", type=str, default=None)

    # capture
    cap_p = subparsers.add_parser("capture", help="Only capture a session")
    cap_p.add_argument("--cmd", type=str, default=None, help="Command to run")
    cap_p.add_argument("--use", type=str, choices=["auto", "pty", "script"], default="auto")
    cap_p.add_argument("--output", type=str, default=None)

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
        print("[loopster] capture (stub)")
        return 0
    if args.command == "analyze":
        print("[loopster] analyze (stub)")
        return 0
    if args.command == "summarize":
        print("[loopster] summarize (stub)")
        return 0
    if args.command == "config":
        print("[loopster] config (stub)")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
