# HoneyHive Customer Support Demo

Demo customer support agent showcasing **evaluation-driven development** with HoneyHive:
- **Observe**: Full visibility into agent execution (sessions, traces, spans)
- **Evaluate**: Systematic measurement against ground truth (experiments, metrics)
- **Iterate**: Data-driven improvements with before/after comparison

Perfect for a 15-20 minute Solutions Engineer demo showing how to debug and improve multi-step AI agents.

---

## 🚀 Quick Demo Setup (5 minutes)

**See [`DEMO_GUIDE.md`](DEMO_GUIDE.md) for complete demo setup and delivery guide**

```bash
# 1. Setup environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY and HONEYHIVE_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate demo data (creates sessions + experiments)
python -m customer_support_agent.main \
  --run \
  --version demo-v1 \
  --run-id demo \
  --experiment

# 4. Open app.honeyhive.ai to verify:
#    - Log Store → Sessions (detailed traces)
#    - Experiments → Metrics and evaluation results
```

**Expected:** 70% pass rate (7/10 tickets), clear failure cases for debugging showcase

---

## 📚 Documentation

| Guide | Purpose |
|-------|---------|
| **[DEMO_GUIDE.md](DEMO_GUIDE.md)** | **START HERE** - Complete setup and delivery guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture overview |
| [AGENTS.md](AGENTS.md) | How the 3-step agent works |

---

## HoneyHive Integration

This demo shows both **session-based tracing** and **experiment tracking**.

### Sessions (Log Store) - For Debugging

**What it is:** Detailed execution traces of your agent processing tickets.

**How to generate:**
```bash
# Basic run (sessions only)
python -m customer_support_agent.main --run --version v1

# With custom run ID
python -m customer_support_agent.main --run --version v1 --run-id my-test-run
```

**Where to find it:**
- Navigate to: **app.honeyhive.ai → Log Store → Sessions**
- Session name: "Demo Session [uuid]"
- Click into session → see span tree (route → retrieve → generate)
- Click any span → see inputs, outputs, latency, tokens

**Demo value:** Debug failures by seeing exact LLM outputs and identifying which step broke

### Experiments - For Measurement

**What it is:** Systematic evaluation against ground truth with aggregate metrics.

**How to generate:**
```bash
# Run with experiment tracking
python -m customer_support_agent.main \
  --run \
  --version v1 \
  --run-id my-experiment \
  --experiment
```

**Where to find it:**
- Navigate to: **app.honeyhive.ai → Experiments**
- Experiment name: "Customer Support Experiment - v1"
- See metrics: routing accuracy, keyword coverage, action steps
- Click test case → see individual results
- Click through to session trace for debugging

**Demo value:** Identify bottlenecks (e.g., routing 75%, keywords 75%) and know exactly what to improve

### Datasets (Ground Truth)

**What it is:** Test cases with expected correct answers for measurement.

**How it works:** Embedded programmatically - no manual upload needed!

When you run with `--experiment`, the code:
1. Loads 10 test cases from `data/mock_tickets.py`
2. Loads ground truth labels from `data/ground_truth.py`
3. Formats as HoneyHive dataset
4. Passes directly to `evaluate()` function

**Optional manual upload:**
```bash
# Generate dataset JSON file
python scripts/create_dataset.py

# Then upload via app.honeyhive.ai → Datasets (if you want centralized management)
```

**Where visible:** In experiment results (expand test case to see inputs and ground_truths)

### Evaluators

**What they are:** Functions that compare agent outputs to ground truth and assign scores.

**Pre-configured evaluators:**
- `routing_accuracy` - Checks category classification
- `keyword_coverage` - Verifies response contains expected keywords
- `has_action_steps` - Ensures numbered steps in response
- `llm_faithfulness` - Checks if response is grounded in docs (optional, uses OpenAI)
- `llm_safety` - Checks for harmful content (optional, uses OpenAI)

**How they work:** Automatically run during experiments, no configuration needed.

---

## Project Structure

```
honeyhivedemo/
├── DEMO_GUIDE.md                  # Complete demo setup and delivery guide
├── README.md                      # This file
├── customer_support_agent/
│   └── main.py                    # CLI entrypoint
├── agents/
│   └── support_agent.py           # 3-step agent: route → retrieve → generate
├── data/
│   ├── mock_tickets.py            # 10 test cases (enhanced for demo story)
│   ├── ground_truth.py            # Expected outputs for evaluation
│   ├── knowledge_base.py          # Support docs by category
│   └── datasets.py                # Dataset loader
├── evaluators/
│   ├── routing_evaluator.py       # Category classification accuracy
│   ├── keyword_evaluator.py       # Response keyword coverage
│   ├── action_steps_evaluator.py  # Response formatting check
│   ├── llm_faithfulness_evaluator.py  # Doc grounding check
│   └── composite_evaluator.py     # Overall pass/fail
├── utils/
│   ├── honeyhive_experiment.py    # HoneyHive evaluate() integration
│   └── exporters.py               # JSON export helpers
└── scripts/
    └── create_dataset.py          # Generate dataset JSON (optional)
```

---

## Command Reference

### Basic Commands

```bash
# Run pipeline (sessions only)
python -m customer_support_agent.main --run

# Run with version tag
python -m customer_support_agent.main --run --version v1

# Run with both sessions and experiments
python -m customer_support_agent.main --run --version v1 --experiment

# Run with custom run ID
python -m customer_support_agent.main --run --version v1 --run-id my-test

# Export results to JSON
python -m customer_support_agent.main --run --export --output results.json

# Debug mode (verbose logging)
python -m customer_support_agent.main --run --debug
```

### Provider Options

```bash
# Use Anthropic Claude (default)
python -m customer_support_agent.main --run --provider anthropic

# Use OpenAI GPT
python -m customer_support_agent.main --run --provider openai

# Offline mode (heuristic routing, no LLM calls)
python -m customer_support_agent.main --run --offline
```

### Model Comparison

```bash
# Run with Anthropic
python -m customer_support_agent.main \
  --run --version anthropic-v1 --experiment

# Run with OpenAI
python -m customer_support_agent.main \
  --run --version openai-v1 --provider openai --experiment

# Compare results in HoneyHive UI (Experiments tab)
```

### Dataset Management

```bash
# Generate dataset JSON for manual upload (optional)
python scripts/create_dataset.py

# Output: honeyhive_dataset.json (10 test cases with ground truth)
```

---

## Environment Variables

Required in `.env`:

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...      # Required for Anthropic provider
HONEYHIVE_API_KEY=hh_...          # Required for HoneyHive integration
OPENAI_API_KEY=sk-proj-...        # Optional, for OpenAI provider

# HoneyHive Configuration
HONEYHIVE_PROJECT=honeyhivedemo   # Project name in HoneyHive
HONEYHIVE_OTLP_ENDPOINT="https://api.honeyhive.ai/opentelemetry/v1/traces"
OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeyhive.ai/opentelemetry/v1/traces"
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://api.honeyhive.ai/opentelemetry/v1/traces"

# Optional
DEBUG=True                        # Enable debug logging
ENVIRONMENT=development           # Environment tag
```

---

## What Makes This Demo Special

### Realistic Test Data
- 10 customer support issues across 3 categories
- **Issue #3** designed to fail (ambiguous "download" → routing confusion)
- **Issue #8** shows pattern (technical term ambiguity)
- ~70% pass rate - not perfect, shows room for improvement

### Clear Error Cascade
- Issue #3: Wrong routing → wrong docs → wrong response
- Visible in session trace (click spans to see exact failure point)
- Perfect for demonstrating "Observe" section of demo

### Measurable Bottlenecks
- Metrics identify weak areas (routing 75%, keywords 75%)
- Shows where to focus improvement efforts
- Perfect for demonstrating "Evaluate" section of demo

### Complete Workflow
- Observe (debugging) → Evaluate (measurement) → Iterate (improvement)
- Shows evaluation-driven development in action
- 15-20 minute demo that tells a compelling story

---

## Development

### Run Tests
```bash
pytest
```

### Test Coverage
```bash
pytest --cov=agents --cov=evaluators
```

### Code Structure
- **Agents:** 3-step pipeline with `@trace` decorators for HoneyHive
- **Evaluators:** Modular evaluators that work with both inline and HoneyHive experiments
- **Data:** Mock tickets enhanced for demo story arc
- **Utils:** HoneyHive integration using `evaluate()` framework

---

## Notes

- **Offline mode:** Agent falls back to heuristic routing when no API key available
- **Provider switching:** Use `--provider anthropic|openai` with corresponding API keys
- **Tracing:** Uses HoneyHive's `@trace` decorator for automatic span creation
- **Experiments:** Uses HoneyHive's `evaluate()` framework for systematic testing
- **HoneyHive SDK:** v0.2.57 (stable) - see `requirements.txt`

---

## Support

- **HoneyHive Docs:** https://docs.honeyhive.ai
- **Demo Guide:** [DEMO_GUIDE.md](DEMO_GUIDE.md)
- **Issues:** GitHub issues or HoneyHive support

---

**Ready to show evaluation-driven development in action!** 🚀
