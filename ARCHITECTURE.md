# Architecture Overview

This demo implements a 3-step customer support agent with tracing, evaluation, and export capabilities. It is intentionally lightweight and in-memory.

## High-Level Flow
1. **Inputs**: mock tickets (`data/mock_tickets.py`).
2. **Agent pipeline** (`agents/support_agent.py`):
   - Step 1: `route_to_category(issue)` – LLM (Anthropic/OpenAI) or heuristic routing.
   - Step 2: `retrieve_docs(category)` – deterministic KB lookup.
   - Step 3: `generate_response(issue, docs, category)` – LLM or templated response with structured outputs (`answer`, parsed `steps`, `category`, `reasoning`, `safety_flags`).
3. **Tracing**: `tracing/tracer.py` records step inputs/outputs/latencies; HoneyHive auto-instrumentation is initialized in `customer_support_agent/main.py` when env vars are set. `@trace` decorators wrap route/retrieve/generate (including OpenAI sub-spans).
4. **Evaluations** (`evaluators/`): routing accuracy, keyword coverage, action steps, format, safety (code), plus optional LLM evaluators (faithfulness, safety).
5. **Export**: results and summary stats emitted via `utils/exporters.py` (JSON/HoneyHive-ready).

## Key Components
- **Agents**: `CustomerSupportAgent` orchestrates the 3-step pipeline, switches between Anthropic/OpenAI/heuristics, and collects traces.
- **Tracing**:
  - Internal tracer: `tracing/tracer.py` tracks per-step spans for demo/export.
  - HoneyHive: `HoneyHiveTracer.init` in `customer_support_agent/main.py`; `@trace` on route/generate enables span capture for LLM calls.
- **Data**: in-memory ticket set, knowledge base, and ground truth (`data/`).
- **Evaluators**: code-based (routing/keyword/action/format/safety) and optional LLM judges (faithfulness/safety) to score outputs and identify bottlenecks.
- **CLI**: `customer_support_agent/main.py` handles run, export, evaluate, compare, debug logging, provider selection, and HoneyHive send.

## Providers & Config
- **Providers**: selectable via `--provider anthropic|openai`. Default model: Anthropic `claude-3-7-sonnet-20250219`; OpenAI default `gpt-4o-mini`.
- **Env vars**:
  - LLM: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
  - HoneyHive: `HONEYHIVE_API_KEY`, `HONEYHIVE_PROJECT`, `HONEYHIVE_SOURCE`, `HONEYHIVE_SESSION`, `HONEYHIVE_OTLP_ENDPOINT` (defaults set in code/sitecustomize).
  - App: `ENVIRONMENT`, `DEBUG`, optional `OPENAI_MODEL`.

## Error Handling & Fallbacks
- LLM calls are wrapped with try/except; on error the agent switches to deterministic responses and disables further LLM use for the run.
- Responses include keyword padding per category to satisfy keyword coverage evaluator.
- `raw_response` is stored JSON-safe for exports; parsing failures are noted in the trace.

## Testing
- **Unit**: `tests/test_agent.py`, `tests/test_evaluators.py`.
- **Integration (opt-in)**: `tests/test_honeyhive_integration.py` (requires live keys and network).
- Pytest markers: `integration` registered in `pytest.ini`.

## Files of Interest
- `agents/support_agent.py` – core pipeline, provider selection, tracing decorators.
- `customer_support_agent/main.py` – CLI, logging, HoneyHive init, orchestration.
- `utils/exporters.py` – JSON export and optional HoneyHive SDK logging.
- `AGENTS.md` – agent-specific usage guide.
