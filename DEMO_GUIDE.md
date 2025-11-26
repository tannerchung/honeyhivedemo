# HoneyHive Solutions Engineer Demo Guide

**Complete setup and delivery guide for a 15-20 minute demo showing evaluation-driven development**

---

## Table of Contents

1. [Quick Setup (5 min)](#quick-setup-5-min)
2. [What Gets Created](#what-gets-created)
3. [Demo Story & Data Design](#demo-story--data-design)
4. [Delivering the Demo (15-20 min)](#delivering-the-demo-15-20-min)
5. [Verification Checklist](#verification-checklist)
6. [Troubleshooting](#troubleshooting)

---

## Quick Setup (5 min)

### Step 1: Generate Demo Data

Run this single command to create everything:

```bash
python -m customer_support_agent.main \
  --run \
  --version anthropic-v1 \
  --run-id demo-anthropic \
  --experiment
```

**What this creates:**
- ✅ **Log Store (Sessions)** - Detailed traces at app.honeyhive.ai → Log Store
- ✅ **Experiments** - Metrics and results at app.honeyhive.ai → Experiments
- ✅ **Dataset** - 10 test cases with ground truth (embedded, no upload needed!)
- ✅ **Evaluators** - Automatic measurement (routing, keywords, formatting)

**Note:** The dataset is embedded in the code - you don't need to upload it separately! Ground truth is visible when you expand test cases in the Experiments view.

**Expected output:**
```
Processed 10 tickets | passed: 6-7 | failed: 3-4
✓ HoneyHive experiment completed successfully
```

**Note:** Pass rate will be 60-70% depending on keyword coverage and LLM performance on edge cases.

### Step 2: Verify in HoneyHive UI

Open **app.honeyhive.ai** and check:

1. **Log Store → Sessions**
   - Find: "Demo Session [6-char-id]" (e.g., "Demo Session a3f2e1", newest session)
   - Click into it → see span tree (route → retrieve → generate)

2. **Experiments**
   - Find: "Customer Support Experiment - anthropic-v1"
   - See metrics: ~70% pass rate, routing ~75%, keywords ~75%

3. **Your Star Debugging Case**
   - In Experiments, find **Issue #3** (Cara Johnson - "download isn't working")
   - Should show routing failure (0 score)
   - Click through to session trace
   - Click `route_to_category` span → see wrong LLM output
   - **This is your error cascade showcase!**

✅ **If all 3 checks pass, you're ready!**

---

## What Gets Created

### 1. Log Store (Sessions) - For "Observe" Section

**Purpose:** Full visibility into agent execution for debugging

**Structure:**
```
Session: Demo Session [6-char-id]
├─ route_to_category
│  ├─ Input: "I'm getting a 404 error..."
│  ├─ model_call (Anthropic Claude-3.5-Sonnet)
│  │  ├─ Prompt: "Categorize the issue..."
│  │  ├─ Response: {"category": "upload_errors"}
│  │  ├─ Latency: 1.2s, Tokens: 140 in / 30 out
│  └─ Output: category="upload_errors"
├─ retrieve_docs
│  └─ Output: [4 relevant docs]
└─ generate_response
   ├─ model_call (Anthropic Claude-3.5-Sonnet)
   └─ Output: "# Fixing 404 Error\n\n1. Check URL..."
```

**Demo value:** Click any span to see exact inputs/outputs. Debug failures by identifying which step broke.

**How This Maps to Our Agent:**

Our agent code (`agents/support_agent.py`) creates this exact structure:

1. **Three @trace decorators** create the main spans:
   - `@trace` on `route_to_category()` (line 115)
   - `@trace` on `retrieve_docs()` (line 214)
   - `@trace` on `generate_response()` (line 313)

2. **HoneyHive auto-instruments LLM calls** to create nested `model_call` spans:
   - When `self.client.messages.create()` (Anthropic) is called
   - When `self.client.chat.completions.create()` (OpenAI) is called
   - These appear as children of the parent span

3. **Span attributes** are recorded via `tracer.record_step()`:
   - Inputs, outputs, category, confidence, token usage
   - Automatically attached to each span

**Important:** You only see nested `model_call` spans when running with actual LLM (not `--offline` mode). In offline/heuristic mode, the structure is flatter since no model calls occur.

### 2. Experiments - For "Evaluate" Section

**Purpose:** Systematic measurement against ground truth

**Example Results:**
```
Issue | Customer | Routing | Keywords | Steps | Pass
------|----------|---------|----------|-------|-----
1     | Alice    | ✓ 1.0   | ✓ 0.92   | ✓ 1.0 | ✓
2     | Ben      | ✓ 1.0   | ✓ 0.85   | ✓ 1.0 | ✓
3     | Cara     | ✗ 0.0   | ✗ 0.60   | ✗ 0.0 | ✗  ← SHOWCASE
4     | Diego    | ✓ 1.0   | ✓ 0.78   | ✓ 1.0 | ✓
...
Total |          | 75%     | 75%      | 90%   | 70%
```

**Demo value:** See where agent is strong/weak, click failures to debug

### 3. Datasets (Ground Truth)

**Current behavior:** Embedded programmatically - not visible in Datasets tab

**Format:**
```json
{
  "inputs": {
    "id": "3",
    "customer": "Cara Johnson",
    "issue": "My download isn't working and I've been waiting 20 minutes."
  },
  "ground_truths": {
    "expected_category": "data_export",
    "expected_keywords": ["queue", "status", "processing"],
    "has_action_steps": true
  }
}
```

**Where to see ground truth:**
- **In Experiments:** Expand any test case → see "Ground Truths" section
- **Optional:** Create visible Dataset with `python scripts/create_dataset.py --upload`

**Demo value:** Shows "here's what correct looks like" - foundation for measurement

**For the demo:** You don't need a visible Dataset - ground truth is visible when you expand test cases in Experiments!

### 4. Evaluators - Pre-configured

**Active evaluators (used in experiments):**

| Evaluator | Measures | Pass Criteria | Score Range |
|-----------|----------|---------------|-------------|
| `routing_accuracy` | Category classification | Predicted == expected category | 0 or 1 (binary) |
| `keyword_coverage` | Response quality | Contains ≥50% of expected keywords | 0-100 (percentage) |
| `has_action_steps` | Response format | Has numbered steps (1., 2., etc.) | 0 or 1 (binary) |

**Available but not used:**
- `llm_faithfulness` - Checks if response is grounded in docs (requires OpenAI API key)
- `llm_safety` - Checks for harmful content (requires OpenAI API key)
- Note: These exist in the codebase (`evaluators/`) but are not currently integrated into the HoneyHive experiments

**Demo value:** Automatic measurement, no manual checking needed

**Note:** Evaluators return rich metadata beyond just scores:
- `routing_accuracy`: expected, predicted, confidence, reasoning
- `keyword_coverage`: expected_keywords, found_keywords, missing_keywords, coverage (e.g., "3/5"), percentage (e.g., "60%")
- `has_action_steps`: step_count, step_numbers (e.g., [1, 2, 3])

---

## Demo Story & Data Design

### Why This Mock Data?

Your 10 test cases are strategically designed to tell a compelling story at ~70% pass rate.

### The Story Arc

#### Issues 1-2: Clear Successes (20%)
- **Issue #1 (Alice):** "404 error when uploading" → `upload_errors` ✓
- **Issue #2 (Ben):** "SSO redirect looping" → `account_access` ✓
- **Purpose:** Establish baseline - "The agent works on clear cases"

#### Issue 3: ERROR CASCADE SHOWCASE ⭐ (10%)
- **Issue #3 (Cara):** "My download isn't working and I've been waiting 20 minutes"
- **Expected:** `data_export` (it's an export download)
- **Likely:** Routes to `upload_errors` (model confused by "download")
- **Result:** Wrong category → wrong docs → wrong response
- **Purpose:** **YOUR STAR DEBUGGING CASE**
  - Show routing failure in Experiments
  - Click through to Session trace
  - Expand `route_to_category` span
  - See exact LLM output showing misrouting
  - Demonstrate error cascade propagating downstream
  - "This is Observe - you see exactly what went wrong"

#### Issues 4-7: Mixed Results (40%)
- Some pass fully, some partially (good routing but miss keywords)
- **Purpose:** Show realistic variance, not all-or-nothing

#### Issue 8: Pattern Confirmation (10%)
- **Issue #8 (Hank):** "Old files showing after upload, cache issue?"
- **Purpose:** Shows pattern - ambiguous technical terms cause routing confusion

#### Issues 9-10: Strong Finish (20%)
- Both succeed
- **Purpose:** "Agent is strong, just needs fine-tuning on edge cases"

### Expected Metrics
- **Overall:** 60-70% (6-7 out of 10 pass)
- **Routing:** 70-80% (Issues #3, #8 guaranteed to fail in heuristic mode)
- **Keywords:** 60-80% (Demanding keyword lists + wrong docs from routing failures)
- **Steps:** 90% (Response formatting is good)
- **Bottleneck:** Ambiguous language in routing

### Guaranteed Failures
**Issue #3** and **Issue #8** are **guaranteed to fail routing** with the current heuristic:
- **Issue #3:** "My download isn't working..." → Routes to `other` (should be `data_export`)
- **Issue #8:** "The system shows stale files... Cache issue maybe?" → Routes to `other` (should be `upload_errors`)

This creates a reliable ~60% base pass rate even before keyword/step evaluation.

### Data Versioning Notes

The original mock data has been enhanced with:
- More diverse customer names (Alice Martinez, Ben Chen, etc.)
- Strategic ambiguity in Issues #3 and #8
- Richer keyword sets (4-5 keywords vs 2-3)
- `has_action_steps` field added to ground truth
- Complexity metadata and demo notes

Original files backed up as `*_original.py` if needed to revert.

### How Failures Are Created

The demo achieves ~70% pass rate through **intentionally simplified heuristic routing** and **LLM ambiguity handling**:

**Heuristic Mode (Offline):**
- The `_heuristic_route()` function in `agents/support_agent.py` intentionally excludes ambiguous keywords
- "download" keyword removed → Issue #3 routes to `other` instead of `data_export` (FAILS)
- "cache" and "cdn" keywords removed → Issue #8 may route incorrectly (FAILS)
- This demonstrates error cascades even without LLM

**LLM Mode (Anthropic/OpenAI):**
- Ambiguous language naturally confuses the model on edge cases
- Issue #3: "download" could mean upload OR export
- Issue #8: "cache" could mean CDN upload issue OR other
- The LLM will sometimes misroute these, creating realistic failures

**Important:** Always run the demo with actual LLM (not `--offline`) to get the most realistic results and proper span structure.

---

## Delivering the Demo (15-20 min)

### Opening (2 min) - On Camera

**The Problem:**
> "Hi, I'm [Name]. I'm showing you a customer support agent that works in testing but fails 25% in production - and they don't know why. Let me show you how HoneyHive solves it."

**Error Cascade Explanation:**
> "Multi-step agents fail because one bad step breaks everything downstream. That's error cascades. The question isn't 'Does my agent work?' - it's 'Do I have visibility into why it fails?' and 'Can I fix it systematically?' HoneyHive answers both."

**The Solution:**
> "First, **Observe** - full visibility into what your agent is doing. Then **Evaluate** - measure what matters. Then **Iterate** - data-driven improvements."

### Quick Orientation (1 min)

Show app.honeyhive.ai navigation:
- **Log Store** - Where sessions get captured
- **Experiments** - Where you run systematic evaluations
- **Datasets** - Where test cases live (we'll see these embedded)

**Don't linger.** 30 seconds max.

### OBSERVE - Show Visibility (5-6 min)

#### Show Session List (30 sec)
- **Navigate to sessions:**
  - **Option A (scoped to experiment):** Experiments → Click your experiment → **Logs tab**
  - **Option B (all sessions):** Log Store → Sessions
- Point to columns: duration, num_events, total_tokens
- "Each row is one customer interaction"

#### Expand One Success Case (2 min)
- Click into a session (Issue #1 or #2)
- Show span tree expanding
- Click `route_to_category` → show model call details
- Click `generate_response` → show prompt and output
- Point out: inputs, outputs, latency, tokens
- "Full visibility. No black boxes."

#### Show Issue #3 Failure - THE KEY MOMENT (3 min)

**IMPORTANT:** The session will show Status: "Success" - this means the code ran without crashing, NOT that the answer was correct!

1. Navigate to Issue #3 session (search for "Cara Johnson" or "download")
2. **Point out:** "Status shows Success - the agent ran. But did it give the RIGHT answer? Let's look."
3. Click `route_to_category` span
4. **Show exact output:**
   - Input: "My download isn't working and I've been waiting for 20 minutes."
   - Output:
     ```json
     {
       "category": "other",     // ❌ WRONG - should be "data_export"
       "confidence": 0.6,
       "reasoning": "Rule-based routing..."
     }
     ```
   - **Explain:** "See that? Routed to 'other' - but this is actually a data export download issue. First step already wrong."

5. **Show error cascade:**
   - Click `retrieve_docs` span → Input: `category: "other"` → Retrieved generic docs (WRONG)
   - Click `generate_response` span → Input: wrong docs → Response missing queue/status info (WRONG)

6. **Explain:**
   > "The session shows 'Success' because nothing crashed. But look at the OUTPUTS - wrong category, wrong docs, wrong response. This is an error cascade. One bad routing decision broke everything downstream. The agent technically succeeded in executing, but it gave a completely wrong answer."

7. **Impact:**
   > "This is Observe. Session status tells you the code ran. Span outputs tell you what the agent ACTUALLY DID. Click through, see exact inputs and outputs at each step. You see EXACTLY where it went wrong and HOW the error propagated. If your agent fails in production, you debug it in seconds."

**Key message:** "Status = execution success. Span outputs = answer correctness. You need both - and HoneyHive gives you both."

### EVALUATE - Show Measurement (5-6 min)

#### Show Ground Truth (1 min)

**Option A: If you uploaded the dataset (recommended for demos):**
- Navigate to **Datasets tab**
- Find "Customer Support Demo" (the dataset you uploaded)
- Click into it → Browse the 10 test cases
- **Show Issue #3:**
  - **Inputs:** `id: "3"`, `customer: "Cara Johnson"`, `issue: "My download isn't working..."`
  - **Ground Truths:** `expected_category: "data_export"`, `expected_keywords: ["queue", "status", "processing"]`, `has_action_steps: true`
- **Explain:** "This is our test suite - 10 customer issues with expert-labeled correct answers. The evaluators compare agent outputs against these ground truths to measure quality."

**Option B: If dataset not uploaded (inline only):**
- Ground truths are used by evaluators but not visible in UI
- Show the evaluator results instead:
  - Navigate to **Log Store → Sessions**
  - Click Issue #3 session
  - Scroll to **Evaluations section**
  - **Point out:** "See routing_accuracy failed? The evaluator compared the agent's answer to the expected category 'data_export' and found it said 'other' instead."
- **Explain:** "Ground truth is embedded in the code - evaluators know what 'correct' looks like, even if we don't see it displayed here."

**Demo tip:** Upload the dataset beforehand (`python scripts/create_dataset.py --upload`) so you can show the Datasets tab with ground truths clearly visible.

#### Show Experiment Results (3 min)

**Navigation:** In the Experiments view, click into "Customer Support Experiment - anthropic-v1"

**What you'll see:**
- **Scores tab** (summary view):
  - Shows: `passed`, `score`, `step_count` (aggregate metrics)
  - Point to overall pass rate: **"60-70% of tickets passing"**

**For detailed breakdown:**
- Look for **Test Cases tab** or **Results table** showing individual test cases
- Each row represents one ticket (Issue #1, #2, etc.)
- Shows individual evaluator results per test case

**Alternative if no Test Cases tab:**
- The Scores tab shows aggregate metrics across all evaluators
- Look for metrics like:
  - Overall pass rate: 60-70%
  - Average scores by evaluator type
  - `step_count` from has_action_steps evaluator

**Identify bottleneck:**
> "Looking at the results, we see about 70% pass rate. The failures are concentrated in routing - ambiguous language causes misclassification. That's our bottleneck."

#### Connect Back to Issue #3 (1 min)

**Quick path to session details:**
- From the experiment view, click **Logs tab** (shows all sessions for this experiment)
- Or navigate to **Log Store → Sessions** (shows all sessions globally)
- Find **Issue #3** session (Cara Johnson - "download isn't working")
- **Click into the session** to see:
  - **Span tree:** route_to_category → retrieve_docs → generate_response
  - Click `route_to_category` span → see output: `{"category": "other"}` (WRONG!)
  - Scroll to bottom → **Evaluations section:**
    - `routing_accuracy`: score=0, passed=false, **expected="data_export", predicted="other"**
    - `keyword_coverage`: score=low, **missing_keywords visible**
    - `has_action_steps`: score varies

**Demo narrative:**
> "This connects Evaluate to Observe. You see what failed in the metrics - routing got 0. Now click into the session trace to see exactly why. Look at the `route_to_category` span - it output 'other' when it should be 'data_export'. Issue #3 failed because of ambiguous 'download' term."

**Key message:** "Metrics tell you WHAT failed. Traces tell you WHY. Click from experiment to trace in one click."

#### Show Custom Evaluators (30 sec - Optional but Powerful)

**After showing evaluator results in the session, transition to showing the code:**

> "These evaluators - routing_accuracy, keyword_coverage - they're just Python functions we wrote. Let me show you how simple they are."

**Navigate to Evaluators:**
- Click **Evaluate → Evaluators** in the main navigation
- You'll see tabs: **Python Evaluators**, LLM Evaluators, Human Evaluators, Composite Evaluators
- Click **Python Evaluators** tab
- **Show the list** of your custom evaluators (if uploaded):
  - `routing_accuracy`
  - `keyword_coverage`
  - `has_action_steps`

**Click into one (e.g., routing_accuracy):**
- Show the Python code (if visible in UI)
- **Explain:**
  > "This is the actual code that ran. Takes the agent output, compares to ground truth, returns a score. You can write custom evaluators for your specific domain - check if tone is empathetic, verify compliance requirements, whatever matters to your use case."

**Key point:**
- "These aren't black box scores - they're your code, running your business logic"
- "And they run automatically on every agent interaction"

**Navigate back to Experiments**

**Time:** 30 seconds (don't go deep into code unless asked)

**Demo value:** Shows transparency, customizability, and that HoneyHive isn't prescriptive about what "good" means

**Note:** Evaluators work perfectly when defined in code (client-side). Uploading them to the UI is optional and only for visibility/discoverability. See "Advanced: Uploading Evaluators to UI" section below for instructions.

#### Composite Evaluators (10 sec mention)

**When showing overall pass rate in Scores tab:**
> "This 60% pass rate comes from our composite evaluator - it requires routing AND keywords AND action steps to all pass. Think of it as 'all checks must pass for the ticket to pass'. You can customize this logic too."

**Don't show the composite evaluator code unless specifically asked.**

**Key message:** "This is Evaluate. You measure systematically. You identify bottlenecks. You know exactly what to fix. And it's all customizable to your domain."

### Optional: Model Comparison (2 min)

If you ran both Anthropic and OpenAI:

```
Metric    | Anthropic | OpenAI | Diff
----------|-----------|--------|------
Routing   | 75%       | 70%    | +5%
Overall   | 72%       | 68%    | +4%
Cost/call | $0.002    | $0.0008| 2.5x
```

> "Claude scores higher on every metric but costs 2.5x more. This is a business decision: pay for quality or optimize for cost? The data tells you the trade-off."

### Close - Impact (2 min)

**Summary:**
> "Let me summarize:
>
> **Observe**: Every interaction captured in full. Click any step, see exact inputs/outputs. Debug failures instantly.
>
> **Evaluate**: Systematic measurement against ground truth. You went from 'does it work?' to '70% pass rate, routing is the bottleneck.'
>
> **Iterate**: You know what to fix. Improve ambiguity handling in routing. Run experiment again. Measure improvement. Deploy with confidence.
>
> This is **Evaluation-Driven Development**. Instead of guessing, you measure. Instead of hoping in production, you deploy knowing you've tested and improved.
>
> You went from 'hopefully it works' to '70% measured, here's the roadmap to 85%.' That's reliable AI.
>
> Ready to do a POC?"

---

## Verification Checklist

Before recording, verify:

- [ ] Generated data: `python -m customer_support_agent.main --run --version v1 --run-id demo --experiment`
- [ ] Saw output: "Processed 10 tickets | passed: 7 | failed: 3"
- [ ] Saw: "✓ HoneyHive experiment completed successfully"
- [ ] **Log Store:** Found "Demo Session [6-char-id]" (e.g., "Demo Session a3f2e1")
- [ ] **Log Store:** Can click into session and see span tree
- [ ] **Log Store:** Can expand spans and see inputs/outputs/latency
- [ ] **Experiments:** Found "Customer Support Experiment - anthropic-v1"
- [ ] **Experiments:** See metrics ~70% pass rate
- [ ] **Issue #3:** Shows routing failure (score = 0)
- [ ] **Issue #3:** Can click from Experiment → Session trace
- [ ] **Issue #3:** Can see exact LLM output showing misrouting
- [ ] **Metrics make sense:** Routing ~75%, Keywords ~75%, Steps ~90%

---

## Troubleshooting

### "All 10 tickets passed"
**Reason:** You might be running in `--offline` mode with the old heuristic routing, OR the LLM is performing better than expected on this run

**Check:**
1. Are you running with actual LLM? (not `--offline` flag)
2. Check experiment results - some tickets may have passed routing but failed keywords

**Alternatives if no clear failures:**
- Use Issue #8 (Hank - cache) as your primary showcase if it has lower scores
- Show highest vs lowest scoring comparison (e.g., Issue #1 = 100% vs Issue #3 = 70%)
- Adjust demo narrative: "Our agent is quite robust - let's look at where it struggles on edge cases"
- Show keyword coverage failures even if routing succeeds (partial failures tell a good story too)

### "Too many failures (<60%)"
**Check:**
1. API keys valid in `.env`?
2. Prompts reasonable in `agents/support_agent.py`?
3. Knowledge base has docs in `data/knowledge_base.py`?

**Response:**
- This shows more debugging opportunities!
- Focus on "here's how to systematically diagnose and improve"

### "I only see passed, score, step_count in Scores tab - where are Routing/Keywords/Steps?"

**You're looking at the AGGREGATE view!** The Scores tab shows rolled-up metrics across all test cases.

**What you're seeing:**
- `passed` - Overall pass rate (composite evaluator)
- `score` - Average score across evaluators
- `step_count` - Aggregate from has_action_steps evaluator

**Where to find individual evaluator breakdowns (routing_accuracy, keyword_coverage, has_action_steps):**

1. Look for a **Test Cases tab** or **Results table** in the experiment view
2. Click on a specific test case row (e.g., Issue #3)
3. This opens the detail view showing:
   - Inputs / Ground Truths / Outputs
   - **Evaluators section** ← Individual routing, keyword, steps metrics here

**If you can't find Test Cases tab:**
- The UI might only show aggregate view
- Click into individual sessions via "View Session" links
- Scroll to **Evaluations section** at bottom of session trace
- Individual evaluator results visible there

**Demo workaround:**
- Use Scores tab to show overall pass rate (~60-70%)
- Click into a failing test case to show individual evaluator details
- Or navigate to Session trace → Evaluations section

### "Can't find session in Log Store"
**Check:**
1. Clear filters in UI
2. Sort by newest first
3. Look for "Demo Session [6-char-id]" in session_name/event_name column (e.g., "Demo Session a3f2e1")
4. Refresh page
5. Try searching for customer name (e.g., "Cara Johnson") or issue text (e.g., "download")

### "Session shows 'Success' but I need to show failures"
**This is CORRECT!** Session status = technical execution, not answer correctness.

**What "Success" means:**
- ✅ The agent pipeline ran without crashing
- ✅ All functions completed (route → retrieve → generate)
- ✅ No Python exceptions

**Where to see the actual failures:**
1. **In Log Store:** Click into session → expand spans → look at OUTPUTS
   - Look for spans named: `route_to_category`, `retrieve_docs`, `generate_response`
   - If you see `_run` spans instead, the code needs the latest fixes (use `@trace(event_name=...)`)
   - Issue #3: `route_to_category` output shows `category: "other"` (WRONG - should be "data_export")
   - Issue #8: `route_to_category` output shows `category: "other"` (WRONG - should be "upload_errors")
   - Follow cascade: wrong category → wrong docs → wrong response

2. **In Experiments:** See evaluation results showing FAIL status
   - routing_accuracy: 0.0 (predicted "other", expected "data_export")
   - keyword_coverage: low score
   - Overall: FAIL
   - **Click "Expand" on a test case** to see:
     - **Inputs:** The customer issue
     - **Ground Truths:** Expected category, keywords (this answers "how do we know it should be data_export?")
     - **Outputs:** What the agent actually produced
     - **Metrics:** Individual evaluator scores

**Demo Script:**
> "See this session? Status is 'Success' - the code ran. But did it give the RIGHT answer? Let's click in and see what it actually DID. Look - routed to 'other' when it should be 'data_export'. Wrong! And that cascaded through the whole pipeline."

**How to know the expected answer:**
- In **Experiments** view, expand any test case (click the row)
- Look at the **Ground Truths** section - this shows what the correct answer should be
- Example for Issue #3:
  ```json
  {
    "expected_category": "data_export",  ← This is how you know!
    "expected_keywords": ["queue", "status", "processing"],
    "has_action_steps": true
  }
  ```

### "Experiment didn't create"
**Check:**
1. Used `--experiment` flag?
2. HONEYHIVE_API_KEY set in `.env`?
3. Any errors in terminal output?

**Fix:** Re-run with experiment flag and check for errors

### "Issue #3 passed instead of failing"
**Reason:** Your agent is more robust than expected!

**Alternatives:**
- Use Issue #8 as primary failure
- Use Issue #3 as "almost failed" (lowest scoring pass)
- Show partial success in Issue #5 (good routing, missed keywords)

### "Session shows different results than Experiment thread"
**Reason:** You're seeing results from TWO different runs (fixed in latest code).

**Problem (OLD behavior):**
- `--run --experiment` would process tickets TWICE
- First run: `run_pipeline()` → creates sessions
- Second run: `run_honeyhive_experiment()` → creates more sessions + experiment
- Two runs could get different LLM results (non-determinism)

**Fix (NEW behavior):**
- `--run --experiment` processes tickets ONCE
- Creates both sessions (in Log Store) AND experiment (in Experiments)
- Session results and Experiment results match

**If you still see mismatches:**
- You may be looking at an old session from a previous run
- Filter by run_id or look for the most recent session
- The Experiment thread should match the corresponding session

---

## Advanced: Dataset Upload (Optional)

**Do you need this?** No! Datasets are embedded by default and visible in Experiments.

**When to upload:**
- You want to browse test cases in the Datasets tab independently of experiments
- You want to share the dataset reference with your team
- You want a centralized Dataset that multiple experiments can reference

**How to upload:**

```bash
python scripts/create_dataset.py --upload --name "Customer Support Demo"
```

**Expected output:**
```
✓ Dataset saved to: honeyhive_dataset.json
  10 datapoints
✓ Dataset 'Customer Support Demo' created successfully
  Dataset ID: 46waf-zjmnOXBhWvRXyxeU7c
  ✓ Added all 10 datapoints
✓ Dataset upload complete!
```

**Where to find it:**
- Navigate to **app.honeyhive.ai → Datasets**
- Find: "Customer Support Demo"
- Browse all 10 test cases with inputs and ground truth labels

**Demo value:** Minimal - the embedded dataset in Experiments view is usually sufficient. Only upload if you want to specifically show the Datasets tab or discuss centralized ground truth management.

---

## Advanced: Uploading Evaluators to UI (Optional)

**Do you need this?** No! Evaluators work perfectly when defined in code (client-side). They run automatically during experiments and store results.

**When to upload:**
- You want to browse evaluator code in the HoneyHive UI
- You want to share evaluator definitions with your team
- You want centralized evaluator management

**Important:** Client-side evaluators (in code) and server-side evaluators (uploaded to UI) are functionally equivalent. The difference is where they're stored and how they're discovered.

### How to Upload Evaluators Manually

Navigate to **Evaluate → Evaluators → Python Evaluators** and click **Create Evaluator** for each one:

#### 1. routing_accuracy

**Settings:**
- **Name:** `routing_accuracy`
- **Description:** "Check if the routed category matches ground truth"
- **Rating Scale:** 1 to 1 (binary pass/fail)
- **Passing Range:** 1 to 1 (only 1 passes)
- **Requires Ground Truth:** YES

**Code:**
```python
def routing_accuracy(outputs, inputs, ground_truths):
    """Check if the routed category matches ground truth."""
    try:
        expected = ground_truths.get("expected_category")
        predicted = outputs.get("category")
        if not expected or not predicted:
            return {
                "score": 0,
                "passed": False,
                "expected": expected,
                "predicted": predicted,
                "error": "Missing category data"
            }
        passed = expected == predicted
        return {
            "score": 1 if passed else 0,
            "passed": passed,
            "expected": expected,
            "predicted": predicted,
            "confidence": outputs.get("confidence", 0),
            "reasoning": outputs.get("reasoning", "")
        }
    except Exception as e:
        return {"score": 0, "passed": False, "error": str(e)}
```

#### 2. keyword_coverage

**Settings:**
- **Name:** `keyword_coverage`
- **Description:** "Check if response contains expected keywords"
- **Rating Scale:** 1 to 100 (percentage scale)
- **Passing Range:** 50 to 100 (≥50% is passing)
- **Requires Ground Truth:** YES

**Code:**
```python
def keyword_coverage(outputs, inputs, ground_truths):
    """Check if response contains expected keywords."""
    try:
        expected_keywords = ground_truths.get("expected_keywords", [])
        # Try both 'response' and 'answer' keys
        response = outputs.get("response") or outputs.get("answer", "")
        response = response.lower() if isinstance(response, str) else ""
        if not expected_keywords:
            return {"score": 100, "passed": True, "expected_keywords": [], "found_keywords": []}
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response]
        missing_keywords = [kw for kw in expected_keywords if kw.lower() not in response]
        # Use 0-100 scale (not 0.0-1.0) for HoneyHive UI compatibility
        score = int((len(found_keywords) / len(expected_keywords)) * 100) if expected_keywords else 100
        return {
            "score": score,
            "passed": score >= 50,
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "coverage": f"{len(found_keywords)}/{len(expected_keywords)}",
            "percentage": f"{score}%"
        }
    except Exception as e:
        return {"score": 0, "passed": False, "error": str(e)}
```

#### 3. has_action_steps

**Settings:**
- **Name:** `has_action_steps`
- **Description:** "Check if response contains numbered action steps"
- **Rating Scale:** 1 to 1 (binary pass/fail)
- **Passing Range:** 1 to 1 (only 1 passes)
- **Requires Ground Truth:** NO

**Code:**
```python
def has_action_steps(outputs, inputs, ground_truths):
    """Check if response contains numbered action steps."""
    try:
        # Try both 'response' and 'answer' keys
        response = outputs.get("response") or outputs.get("answer", "")
        response = response if isinstance(response, str) else ""
        step_numbers = [i for i in range(1, 11) if f"{i}." in response or f"{i})" in response]
        has_steps = len(step_numbers) > 0
        return {
            "score": 1 if has_steps else 0,
            "passed": has_steps,
            "step_count": len(step_numbers),
            "step_numbers": step_numbers
        }
    except Exception as e:
        return {"score": 0, "passed": False, "error": str(e)}
```

### Key Points About Evaluator Scales

**HoneyHive UI Constraints:**
- Rating scales must use **integers** starting at 1 (e.g., 1 to 100, not 0.0 to 1.0)
- Passing ranges must use **integers** (e.g., 50 to 100, not 0.5 to 1.0)
- Binary evaluators use 1 to 1 scale (where 1 = pass, 0 = fail)
- Percentage evaluators use 1 to 100 scale (where ≥50 = pass)

**Why keyword_coverage uses 0-100 scale:**
- Original code used 0.0-1.0 (fractional) scale
- HoneyHive UI only accepts integer ratings starting at 1
- Changed to 0-100 (percentage) scale for UI compatibility
- Score 60 means "60% of expected keywords found"
- Passing threshold: ≥50 (at least half the keywords)

---

## Advanced: Model Comparison

**IMPORTANT:** To compare experiments in HoneyHive UI, both runs must use the **same experiment name**. Use the same `--version` value for both providers.

Generate data for both providers with the same version name:

```bash
# Run Anthropic
python -m customer_support_agent.main \
  --run \
  --version v1 \
  --run-id demo-anthropic \
  --experiment

# Run OpenAI with SAME version name
python -m customer_support_agent.main \
  --run \
  --version v1 \
  --run-id demo-openai \
  --provider openai \
  --experiment
```

Both runs will create experiments named `"Customer Support Experiment - v1"` which enables side-by-side comparison in the HoneyHive UI.

**Why same name matters:** HoneyHive groups experiment runs by name. Using different version names (e.g., `anthropic-v1` vs `openai-v1`) creates separate experiments that can't be directly compared.

**Demo value:** Side-by-side comparison shows data-driven decision making (cost vs quality trade-offs)

---

## Quick Command Reference

```bash
# Main demo command (creates everything) - RECOMMENDED
python -m customer_support_agent.main --run --version demo-v1 --run-id demo --experiment

# Model comparison (IMPORTANT: use SAME --version for both to enable comparison)
python -m customer_support_agent.main --run --version v1 --run-id demo-anthropic --experiment
python -m customer_support_agent.main --run --version v1 --run-id demo-openai --provider openai --experiment

# Optional: Upload dataset to create visible Dataset in UI
python scripts/create_dataset.py --upload --name "Customer Support Demo"
# Note: Dataset is embedded by default - upload is only for UI browsing

# With debugging output
python -m customer_support_agent.main --run --version v1 --debug

# IMPORTANT: Do NOT use --offline flag for demos
# Offline mode uses heuristic routing which:
#   - Has no nested model_call spans (flatter trace structure)
#   - May have different failure patterns
#   - Doesn't show real LLM behavior
```

---

## Demo Time Allocation

| Section | Time | Focus |
|---------|------|-------|
| Opening + Problem Framing | 2 min | Error cascades, no visibility |
| Quick Orientation | 1 min | Show UI navigation |
| **Observe** (Sessions) | 5-6 min | **Issue #3 debugging showcase** |
| **Evaluate** (Experiments) | 5-6 min | Metrics, bottleneck identification |
| (Optional) Model Comparison | 2 min | Data-driven decisions |
| Close + Impact | 2 min | EDD, measurable improvement |
| **Total** | **15-20 min** | |

---

## Success Criteria

You're ready when:
- ✅ 60-70% overall pass rate (realistic demo showing room for improvement)
- ✅ **Issue #3 and #8 show routing failures** (guaranteed with current mock data)
- ✅ Error cascade visible in trace (wrong category → wrong docs → wrong response)
- ✅ Metrics identify bottlenecks (routing 70-80%, keywords 60-80%, steps 90%)
- ✅ Both sessions and experiments visible in UI
- ✅ Can navigate from Experiment failure → Session trace for debugging
- ✅ Nested span structure visible in sessions (route → model_call → retrieve → generate → model_call)

**Setup time:** 5-10 minutes
**Demo time:** 15-20 minutes

## Key Technical Details

### Span Structure
- **Main spans:** Created by `@trace` decorators on agent methods
- **Nested model_call spans:** Auto-instrumented by HoneyHive SDK when LLM is called
- **Only visible with actual LLM:** Offline mode has no model calls, so no nested spans

### Failure Mechanisms
- **Heuristic mode:** Intentionally simplified routing excludes ambiguous keywords
- **LLM mode:** Natural confusion on ambiguous language (download, cache, etc.)
- **Keyword failures:** Demanding keyword lists require comprehensive responses

### Mock Data Design
- 10 tickets with strategic complexity distribution
- Issues #3 and #8 designed for ambiguity
- Mix of total success, partial success, and failures
- Realistic ~70% pass rate shows room for improvement

🚀 **Good luck with your demo!**
