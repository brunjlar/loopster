# Loopster
Capture, summarize, and analyze CLI sessions with an AI feedback loop that steadily improves your global assistant config.

## Overview
Loopster is a unified CLI that helps you:
- Capture an interactive CLI session (with ANSI/TUI cleanup)
- Summarize the session via an LLM (single model)
- Analyze the session against your global AI agent config (AGENTS.md, GEMINI.md, etc.) to propose careful, project‑agnostic improvements
- Optionally apply the proposed changes safely after diff review
- Inspect supported model names

LLM usage is simple: pass a single `--model` and Loopster infers the provider (OpenAI vs. Google Gemini). We use the same model for summarization and analysis to keep things simple. Authentication uses standard provider environment variables. By default, Loopster uses `gpt-5` unless you set `LOOPSTER_MODEL` or pass `--model`.

## Quick Start
Prereqs:
- Python 3.11+ (3.12/3.13 OK)

Clone and install:
- `git clone https://github.com/brunjlar/loopster`
- `cd loopster`
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`

Set your model and provider keys:
- `export LOOPSTER_MODEL=gpt-5` (or pass `--model` each time)
- For OpenAI: `export OPENAI_API_KEY=...`
- For Google: `export GOOGLE_API_KEY=...`

Run the CLI:
- `python -m loopster --help`

## Getting Started
Follow these steps to verify your setup and see Loopster in action:

1) Verify models and keys
- `loopster models` (prints curated model names)
- Ensure `OPENAI_API_KEY` or `GOOGLE_API_KEY` is set for your chosen model

2) Capture a small session
- `loopster capture --cmd "python -V" --out session.log`
- Optional: keep raw ANSI output with `--raw session.raw`

3) Summarize the session
- `loopster summarize --log session.log --model gpt-5 --format text`

4) Analyze against your global config
- `loopster analyze --log session.log --config ~/.codex/AGENTS.md --model gpt-5`
- Outputs: analysis, updated config proposal, and a unified diff (no changes for simple sessions)

5) End‑to‑end in one go
- `loopster run --cmd "python -V" --config ~/.codex/AGENTS.md --model gpt-5`
- Add `--summary-out`, `--analysis-out`, `--updated-out` to save artifacts
- Add `--apply --yes` to overwrite your global config after safety checks

## Authentication
- OpenAI: set `OPENAI_API_KEY`
- Google Gemini: set `GOOGLE_API_KEY`

No other configuration files are required. For convenience, Loopster also checks `LOOPSTER_MODEL` when `--model` is omitted.

## Commands

### Analyze
Two‑pass analysis to improve your global agent config without polluting it with project‑specific details.

- Pass 1: Project‑agnostic analysis (always printed)
  - `loopster analyze --log session.log --config ~/.codex/AGENTS.md --model gpt-4o-mini --analysis-out analysis.txt`
  - Produces “general lessons” focused on durable policies (reasoning, safety, clarification, retries). Avoids specifics.

- Pass 2: Config update proposal (always printed, plus diff)
  - The analysis and your current config are used to propose careful edits that preserve your original intent.
  - A unified diff is shown. The full updated config is printed, and optionally saved:
    - `--out updated_config.md` to write the proposal to a file

- Apply changes to your actual config (explicit opt‑in)
  - `--apply` prompts for confirmation; `--yes` applies without asking:
    - `loopster analyze --log session.log --config ~/.codex/AGENTS.md --apply --yes --model gpt-4o-mini`
  - Safety checks prevent applying updates that contain likely project‑specific details (URLs, absolute paths, common filenames, git hosts, emails). If detected, apply is aborted, but results remain visible.

Notes:
- `--analysis-out` and `--out` are optional; outputs are always shown on screen.
- The analysis prompt strongly enforces project‑agnostic guidance and use of placeholders (e.g., `<PROJECT>`, `<API_KEY>`).

### Summarize
Generate an LLM summary of a cleaned session log.

- Text output (OpenAI):
  - `loopster summarize --log session.log --format text --model gpt-4o-mini`

- Markdown output (Gemini):
  - `loopster summarize --log session.log --format markdown --model gemini-1.5-flash`

- If `--model` is omitted, Loopster uses `LOOPSTER_MODEL` or defaults to `gpt-5`.

### Models
List a curated set of recognized, text/chat‑suitable models (not exhaustive; availability depends on your provider/account). We intentionally exclude realtime/audio/vision‑only variants.

- `loopster models`

OpenAI examples (text/chat):
- `gpt-4o`, `gpt-4o-mini`
- `o4-mini`, `o3`, `o3-mini`
- `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`

Google Gemini examples (text/chat):
- `gemini-2.5-pro`
- `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b`
- `gemini-2.0-flash`

Test/development:
- `fake:<anything>` — returns `LOOPSTER_FAKE_RESPONSE` or `"OK"` without calling a real API.

Note on audio/vision/realtime models:
- Loopster focuses on text/chat workflows (capturing logs, summarizing, analyzing, and updating global prompts).
- Realtime, audio (STT/TTS), and pure‑vision variants are excluded because they require different SDKs, streaming protocols, or input types not supported by this CLI flow.
- If you need those capabilities, run them via the respective provider SDKs directly; you can still use `loopster capture` to record those sessions and then analyze their logs.

### Capture
Run a command and save a cleaned, human-readable log:

- `loopster capture --cmd "your-cli --args" --out session.log`
- Optional flags:
  - `--no-mirror` to avoid echoing child output to your terminal
  - `--timeout <seconds>` to enforce a timeout (always saves partial logs)
  - `--raw <path>` to write the raw, unsanitized output
  - `--include-invocation` to prepend header lines with the exact invocation

### Sanitize
Convert a raw log (with ANSI/TUI control sequences) into a cleaned text file:

- `loopster sanitize --raw raw.txt --out clean.txt`

## How provider inference works
- Model names imply the provider:
  - Names starting with `gpt-` or `o3`/`o4` → OpenAI
  - Names starting with `gemini-` → Google Gemini
  - Names starting with `fake:` → built-in test model
- Loopster forwards the exact model string to the provider via LangChain.

## Notes
- The models list is curated for convenience; actual support and access vary by account and region.
- For offline tests/demos, use `--model fake:any` and optionally set `LOOPSTER_FAKE_RESPONSE`.
- The analyze apply step refuses to overwrite your global config if the update appears project‑specific; this preserves portability and intent.
## Examples

- End‑to‑end (no apply):
  - `loopster run --cmd "your-cli --arg" --config ~/.codex/AGENTS.md --model gpt-5`

- End‑to‑end with saved outputs and apply:
  - `loopster run --cmd "your-cli --arg" \
      --config ~/.codex/AGENTS.md \
      --model gpt-5 \
      --summary-out summary.txt \
      --analysis-out analysis.txt \
      --updated-out updated.md \
      --apply --yes`

- Analyze existing log (no capture):
  - `loopster analyze --log session.log --config ~/.codex/AGENTS.md --model gpt-5`

- Summarize existing log:
  - `loopster summarize --log session.log --format markdown --model gpt-5`

- Capture and sanitize:
  - `loopster capture --cmd "your-cli --arg" --out session.log --raw session.raw`
  - `loopster sanitize --raw session.raw --out clean.log`

## Design goals and workflow
- Evidence‑driven analysis: Pass 1 compares the session log to your global config and must justify changes with quotes and severity. If there are no major issues, it explicitly returns “Decision: NO‑CHANGE”.
- Minimal, surgical edits: Pass 2 proposes careful updates preserving the user’s intent and structure. Drastic changes are avoided unless the analysis shows severe, systemic failures.
- Project‑agnostic output: The updated config avoids project details, encourages placeholders, and prevents secrets or local paths from leaking into your global prompt.
- Safety by default: Apply is opt‑in, always shows a true diff (computed locally with Python’s `difflib`), and aborts if project‑specific content is detected.
