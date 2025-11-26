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

# 3. (Optional but recommended) Upload dataset for demo
python scripts/create_dataset.py --upload --name "Customer Support Demo"
# This makes ground truths visible in the Datasets tab during demos

# 4. Generate demo data (creates sessions + experiments in ONE run)
python -m customer_support_agent.main \
  --run \
  --version demo-v1 \
  --run-id demo \
  --experiment

# Note: --experiment flag processes tickets ONCE, creating both:
#   - Sessions in Log Store (for debugging)
#   - Experiment in Experiments (for evaluation)
#   - Dataset is embedded (evaluators use it, but not displayed in Experiments UI)

# 5. Open app.honeyhive.ai to verify:
#    - Log Store → Sessions (detailed traces with evaluations)
#    - Experiments → Scores tab (aggregate metrics)
#    - Datasets → "Customer Support Demo" (ground truths visible if uploaded)
```

**Expected:** 60-70% pass rate (6-7/10 tickets pass), with Issues #3 and #8 guaranteed to fail routing

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
- Session name: "Demo Session [6-char-id]" (e.g., "Demo Session a3f2e1")
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

**How it works:** Embedded programmatically by default - no upload needed!

When you run with `--experiment`, the code:
1. Loads 10 test cases from `data/mock_tickets.py`
2. Loads ground truth labels from `data/ground_truth.py`
3. Formats as HoneyHive dataset
4. Passes directly to `evaluate()` function
5. Results visible in Experiments tab (expand test case to see ground truth)

**Optional: Create visible Dataset in UI:**
```bash
# Generate dataset JSON file only (for manual upload or reference)
python scripts/create_dataset.py

# Generate AND upload to create a Dataset entry in HoneyHive UI
python scripts/create_dataset.py --upload --name "Customer Support Demo"

# Expected output:
# ✓ Dataset saved to: honeyhive_dataset.json
#   10 datapoints
# ✓ Dataset 'Customer Support Demo' created successfully
#   Dataset ID: 46waf-zjmnOXBhWvRXyxeU7c
#   ✓ Added all 10 datapoints
# ✓ Dataset upload complete!
```

**Benefits of uploading:**
- Browse test cases in Datasets tab (independent of experiments)
- Share dataset across multiple experiments
- Centralized ground truth management
- Reuse dataset across different agent versions

**Where visible:**
- **In Experiments:** Ground truths are passed to evaluators for scoring, but NOT displayed in the Experiments UI
- **In Sessions:** Evaluator results show comparison (e.g., "expected: data_export, predicted: other")
- **In Datasets tab:** If you uploaded the dataset, ground truths are fully visible and browsable

**Recommendation for demos:** Upload the dataset (`python scripts/create_dataset.py --upload`) so you can show ground truths in the Datasets tab during demos.

### Evaluators

**What they are:** Functions that compare agent outputs to ground truth and assign scores.

**Active evaluators (used in experiments):**
- `routing_accuracy` - Checks category classification (binary: 0 or 1)
- `keyword_coverage` - Verifies response contains expected keywords (percentage: 0-100, passes at ≥50)
- `has_action_steps` - Ensures numbered steps in response (binary: 0 or 1)

**Available but not used:**
- `llm_faithfulness` - Checks if response is grounded in docs (requires OpenAI API key)
- `llm_safety` - Checks for harmful content (requires OpenAI API key)
- Note: These exist in the codebase but are not currently integrated into experiments

**How they work:** Automatically run during experiments, no configuration needed.

**Rich metadata returned:**
- `routing_accuracy`: expected, predicted, confidence, reasoning
- `keyword_coverage`: expected_keywords, found_keywords, missing_keywords, coverage (e.g., "3/5"), percentage (e.g., "60%")
- `has_action_steps`: step_count, step_numbers (e.g., [1, 2, 3])

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
│   ├── routing_evaluator.py       # Category classification accuracy (ACTIVE)
│   ├── keyword_evaluator.py       # Response keyword coverage (ACTIVE)
│   ├── action_steps_evaluator.py  # Response formatting check (ACTIVE)
│   ├── composite_evaluator.py     # Overall pass/fail (ACTIVE)
│   ├── llm_faithfulness_evaluator.py  # Doc grounding check (available, not used)
│   └── llm_safety_evaluator.py    # Safety check (available, not used)
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
# Run pipeline (sessions only, no experiment)
python -m customer_support_agent.main --run

# Run with version tag (sessions only)
python -m customer_support_agent.main --run --version v1

# Run with BOTH sessions and experiments (RECOMMENDED for demos)
# This processes tickets ONCE and creates both sessions and experiment
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

**IMPORTANT:** To compare experiments in HoneyHive UI, both runs must use the **same** `--version` value to create the same experiment name.

```bash
# Run with Anthropic
python -m customer_support_agent.main \
  --run --version v1 --run-id demo-anthropic --experiment

# Run with OpenAI (using SAME version name)
python -m customer_support_agent.main \
  --run --version v1 --run-id demo-openai --provider openai --experiment

# Both create "Customer Support Experiment - v1" for side-by-side comparison
# Compare results in HoneyHive UI (Experiments tab)
```

### Dataset Management

**Do I need to upload a dataset for the demo?** No! The dataset is embedded in the code and automatically used when you run experiments.

**Where can I see the dataset?**
- **In Experiments view:** Expand any test case → see "Ground Truths" section
- **In Datasets tab (optional):** Upload with the command below

**Optional: Create visible Dataset entry in UI:**
```bash
# Generate JSON file only
python scripts/create_dataset.py

# Generate AND upload to HoneyHive
python scripts/create_dataset.py --upload --name "Customer Support Demo"

# Expected output:
# ✓ Dataset saved to: honeyhive_dataset.json
# ✓ Dataset 'Customer Support Demo' created successfully
#   Dataset ID: 46waf-zjmnOXBhWvRXyxeU7c
#   ✓ Added all 10 datapoints
```

**When to upload:**
- You want to browse test cases independently in the Datasets tab
- You want to share the dataset reference with your team
- You want centralized ground truth that multiple experiments can reference

**Bottom line:** For demos, the embedded dataset in Experiments view is sufficient. Upload is optional for convenience.

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

# Optional - these default to HoneyHive OTLP endpoint if not set
# HONEYHIVE_OTLP_ENDPOINT="https://api.honeyhive.ai/opentelemetry/v1/traces"

# Optional
DEBUG=True                        # Enable debug logging
ENVIRONMENT=development           # Environment tag
```

---

## What Makes This Demo Special

### Realistic Test Data
- 10 customer support issues across 3 categories
- **Issue #3** guaranteed to fail (ambiguous "download" without "export" keyword → routes to `other`)
- **Issue #8** guaranteed to fail (ambiguous "cache"/"stale" without "upload" keyword → routes to `other`)
- ~60-70% pass rate - not perfect, shows room for improvement
- Intentionally simplified heuristic routing excludes ambiguous keywords to ensure failures

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
- **Evaluator Scales:** keyword_coverage uses 0-100 (percentage) scale for HoneyHive UI compatibility (not 0.0-1.0)
- **Evaluator Upload:** Evaluators work perfectly in code (client-side). Uploading to UI is optional for visibility only

---

## Support

- **HoneyHive Docs:** https://docs.honeyhive.ai
- **Demo Guide:** [DEMO_GUIDE.md](DEMO_GUIDE.md)
- **Issues:** GitHub issues or HoneyHive support

---

**Ready to show evaluation-driven development in action!** 🚀
