# HoneyHive Customer Support Demo

Demo customer support agent that showcases a 3-step LLM pipeline, per-step evaluation, tracing, and HoneyHive-ready exports.

## Quickstart
- Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY` (or leave blank to use the offline heuristics).
- Install deps: `pip install -r requirements.txt`
- Run the pipeline on mock tickets: `python main.py --run --export`
- Run tests: `pytest`

## Commands
- `python main.py --run` – process mock tickets with tracing.
- `python main.py --run --version v1` – tag a version for iterative runs.
- `python main.py --run --provider openai` – run with OpenAI (requires `OPENAI_API_KEY`).
- `python main.py --run --offline` – force heuristic mode (no external LLM calls).
- `python main.py --export --output results.json` – export the latest run to JSON.
- `python main.py --evaluate results.json` – run evaluators against a saved run.
- `python main.py --compare v1_results.json v2_results.json` – compare iterations.
- `python main.py --send-to-honeyhive results.json` – attempt HoneyHive SDK send (no-op if SDK missing).

## What’s inside
- `agents/support_agent.py` – 3-step pipeline (route, retrieve docs, generate response).
- `evaluators/` – routing, keyword coverage, action steps, and composite evaluators.
- `data/` – mock tickets, knowledge base, ground truth.
- `tracing/tracer.py` – lightweight OpenTelemetry-style tracer.
- `utils/exporters.py` – JSON + HoneyHive-ready export helpers.
- `tests/` – unit tests for the agent and evaluators.

## Notes
- The agent falls back to a deterministic, rule-based mode when no Anthropic API key is available; this keeps tests offline-friendly.
- You can switch providers via `--provider anthropic|openai`; set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` accordingly.
- Traces include timings, inputs, outputs, and raw model payloads to demo observability and error cascades.
