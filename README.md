# Loopster
Capture, analyze, and improve CLI workflows with AI-driven session feedback.

## Overview
Loopster is a unified CLI that helps you:
- Capture an interactive CLI session (with ANSI/TUI cleanup)
- Summarize the session via an LLM
- Inspect supported model names

LLM usage is simple: you pass a `--model` and Loopster infers the provider (OpenAI vs. Google Gemini). Authentication uses standard provider environment variables.

## Install
- Python 3.11+
- Install dependencies:
  - `pip install -r requirements.txt`

## Authentication
- OpenAI: set `OPENAI_API_KEY`
- Google Gemini: set `GOOGLE_API_KEY`

No other configuration files are required. For convenience, Loopster also checks `LOOPSTER_MODEL` when `--model` is omitted.

## Commands

### Summarize
Generate an LLM summary of a cleaned session log.

- Text output (OpenAI):
  - `loopster summarize --log session.log --format text --model gpt-4o-mini`

- Markdown output (Gemini):
  - `loopster summarize --log session.log --format markdown --model gemini-1.5-flash`

- If `--model` is omitted, Loopster uses `LOOPSTER_MODEL` or defaults to `gpt-4o-mini`.

### Models
List a curated set of recognized models (not exhaustive; availability depends on your provider/account):

- `loopster models`

OpenAI examples:
- `gpt-4o`, `gpt-4o-mini`, `gpt-4o-realtime-preview`, `gpt-4o-audio-preview`
- `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
- `o3`, `o3-mini`, `o4-mini`
- `gpt-5`

Google Gemini examples:
- `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b`
- `gemini-1.0-pro`, `gemini-1.0-pro-vision`
- `gemini-2.5-pro`

Test/development:
- `fake:<anything>` — returns `LOOPSTER_FAKE_RESPONSE` or `"OK"` without calling a real API.

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
