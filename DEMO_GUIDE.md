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
- ✅ **Datasets** - 10 test cases with ground truth (embedded)
- ✅ **Evaluators** - Automatic measurement (routing, keywords, formatting)

**Expected output:**
```
Processed 10 tickets | passed: 7 | failed: 3
✓ HoneyHive experiment completed successfully
```

### Step 2: Verify in HoneyHive UI

Open **app.honeyhive.ai** and check:

1. **Log Store → Sessions**
   - Find: "Demo Session [uuid]" (newest session)
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
Session: Demo Session [uuid]
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

### 3. Datasets (Ground Truth) - Embedded

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

**Where visible:** In experiment results (expand test case) and session metadata

**Demo value:** Shows "here's what correct looks like" - foundation for measurement

### 4. Evaluators - Pre-configured

| Evaluator | Measures | Pass Criteria |
|-----------|----------|---------------|
| `routing_accuracy` | Category classification | Predicted == expected category |
| `keyword_coverage` | Response quality | Contains ≥50% of expected keywords |
| `has_action_steps` | Response format | Has numbered steps (1., 2., etc.) |

**Demo value:** Automatic measurement, no manual checking needed

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
- **Overall:** 70-75% (7-8 out of 10 pass)
- **Routing:** 70-80% (Issues #3, #8 fail or score low)
- **Keywords:** 70-80% (Some demanding keyword lists)
- **Steps:** 90% (Response formatting is good)
- **Bottleneck:** Ambiguous language in routing

### Data Versioning Notes

The original mock data has been enhanced with:
- More diverse customer names (Alice Martinez, Ben Chen, etc.)
- Strategic ambiguity in Issues #3 and #8
- Richer keyword sets (4-5 keywords vs 2-3)
- `has_action_steps` field added to ground truth
- Complexity metadata and demo notes

Original files backed up as `*_original.py` if needed to revert.

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
- Navigate to Log Store → Sessions
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
1. Navigate to Issue #3 session
2. Show span tree
3. Click `route_to_category` span
4. **Show exact LLM output:**
   - Input: "My download isn't working..."
   - Output: Routed to `upload_errors` (WRONG - should be `data_export`)
5. **Show error cascade:**
   - Wrong category → retrieved wrong docs
   - Wrong docs → generated wrong response
6. **Explain:**
   > "See? The model saw 'download' and thought upload issue. But it's actually an export download. This first step failure cascaded downstream. Everything after this is wrong because of that routing error."
7. **Impact:**
   > "This is Observe. You see exactly what happened, where it went wrong, and why. No black boxes. Click any step, see the exact LLM output. If your agent fails in production, you debug it in seconds."

**Key message:** "Visibility into error cascades is how you debug multi-step systems."

### EVALUATE - Show Measurement (5-6 min)

#### Show Ground Truth (1 min)
- Navigate to Experiments
- Click into "Customer Support Experiment - anthropic-v1"
- Expand Issue #3 to show:
  - **Inputs:** Customer issue
  - **Ground Truths:** Expected category, keywords
  - **Outputs:** What agent actually produced
- "A domain expert labels what correct looks like. Without this, you can't measure improvement."

#### Show Experiment Results (3 min)
- Show metrics table
- Point to overall: **"70% pass rate - 7 out of 10 tickets"**
- Break down metrics:
  - Routing: 75%
  - Keywords: 75%
  - Action Steps: 90%
- **Identify bottleneck:**
  > "The data tells you where you're weak. Routing is 75% - that's where you need to improve. Specifically, ambiguous language handling."

#### Connect Back to Issue #3 (1 min)
- Click Issue #3 in experiment results
- Show metrics all failed (routing = 0)
- **Link to trace:**
  > "This connects Evaluate to Observe. You see what failed in the metrics, you click the trace to see exactly why. Issue #3: routing failed because of ambiguous 'download' term."

**Key message:** "This is Evaluate. You measure systematically. You identify bottlenecks. You know exactly what to fix."

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
- [ ] **Log Store:** Found "Demo Session [uuid]"
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
**Reason:** Issue #3 wasn't ambiguous enough to confuse the model

**Fix:**
- Use Issue #8 (Hank - cache) as your primary failure showcase
- Or show highest vs lowest scoring comparison
- Adjust demo: "Even our edge cases mostly work - let's see where it struggles"

### "Too many failures (<60%)"
**Check:**
1. API keys valid in `.env`?
2. Prompts reasonable in `agents/support_agent.py`?
3. Knowledge base has docs in `data/knowledge_base.py`?

**Response:**
- This shows more debugging opportunities!
- Focus on "here's how to systematically diagnose and improve"

### "Can't find session in Log Store"
**Check:**
1. Clear filters in UI
2. Sort by newest first
3. Look for "Demo Session [uuid]" in event_name column
4. Refresh page

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

---

## Advanced: Model Comparison

Generate OpenAI data for comparison:

```bash
python -m customer_support_agent.main \
  --run \
  --version openai-v1 \
  --run-id demo-openai \
  --provider openai \
  --experiment
```

**Demo value:** Side-by-side comparison shows data-driven decision making (cost vs quality trade-offs)

---

## Quick Command Reference

```bash
# Main demo command (creates everything)
python -m customer_support_agent.main --run --version demo-v1 --run-id demo --experiment

# Model comparison
python -m customer_support_agent.main --run --version anthropic-v1 --experiment
python -m customer_support_agent.main --run --version openai-v1 --provider openai --experiment

# Generate dataset JSON (optional, for manual upload)
python scripts/create_dataset.py

# With debugging output
python -m customer_support_agent.main --run --version v1 --debug
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
- ✅ 70-75% overall pass rate
- ✅ Issue #3 shows clear routing failure
- ✅ Error cascade visible in trace
- ✅ Metrics identify bottlenecks
- ✅ Both sessions and experiments visible in UI
- ✅ Can navigate from Experiment failure → Session trace for debugging

**Setup time:** 5-10 minutes
**Demo time:** 15-20 minutes

🚀 **Good luck with your demo!**
