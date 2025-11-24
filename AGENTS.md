# Agents Guide

Overview of the customer support agent implementations and how to run them with different providers.

## CustomerSupportAgent
- File: `agents/support_agent.py`
- Steps:
  1. `route_to_category(issue)` – LLM or heuristic routing into `upload_errors`, `account_access`, `data_export`, or `other`.
  2. `retrieve_docs(category)` – deterministic knowledge base lookup.
  3. `generate_response(issue, docs, category)` – LLM or templated response with numbered steps.
- Tracing: every step is recorded via `tracing/tracer.py` (timings, inputs/outputs, raw responses).
- Fallbacks: if an LLM call errors or parsing fails, the agent switches to deterministic responses and disables further LLM calls for the run.

## Providers
- Anthropic (default): set `ANTHROPIC_API_KEY`; model default `claude-3-7-sonnet-20250219`.
- OpenAI: set `OPENAI_API_KEY` and run with `--provider openai`; default model `gpt-4o-mini`.
- Offline: `--offline` forces heuristic routing and templated responses (no external calls).

## CLI Usage
- Default (Anthropic): `python main.py --run --export --output results.json`
- OpenAI: `python main.py --run --provider openai --export --output results.json`
- Offline: `python main.py --run --offline --export --output results.json`
- Debug logging: add `--debug` (logs to stdout and `logs/run.log`).

## Error Handling & Debug
- Network/API issues trigger fallbacks and log debug entries when `--debug` is set.
- `raw_response` is stored JSON-safe for exports; traces include any fallback reasons.
- Routing/generation outputs are still traced to demonstrate error cascades and recovery.
