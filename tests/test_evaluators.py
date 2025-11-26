from evaluators import (
    ActionStepsEvaluator,
    CompositeEvaluator,
    KeywordEvaluator,
    LLMFaithfulnessEvaluator,
    LLMSafetyEvaluator,
    RoutingEvaluator,
    SafetyEvaluator,
)


def _build_result(category: str, response: str):
    return {
        "output": {"category": category},
        "steps": {"generate": {"answer": response}},
        "evaluations": {},
    }


def test_routing_evaluator_pass():
    ticket = {"id": "1"}
    result = _build_result("upload_errors", "Response")
    evaluator = RoutingEvaluator()
    score = evaluator.evaluate(ticket, result)
    assert score["passed"] is True
    assert score["score"] == 5


def test_keyword_evaluator_scores_coverage():
    ticket = {"id": "1"}
    # Response includes enough keywords from ground truth to pass (>= 60%)
    # Issue #1 expects: ['404', 'endpoint', 'url', 'path']
    # Including 3 out of 4 = 75% coverage (passes >= 60% threshold)
    result = _build_result("upload_errors", "404 error at endpoint with path issue")
    evaluator = KeywordEvaluator()
    score = evaluator.evaluate(ticket, result)
    assert score["passed"] is True
    assert score["score"] >= 0.6


def test_action_steps_evaluator_detects_steps():
    ticket = {"id": "1"}
    result = _build_result("upload_errors", "1. do this\n2. do that")
    evaluator = ActionStepsEvaluator()
    score = evaluator.evaluate(ticket, result)
    assert score["passed"] is True


def test_composite_evaluator_requires_all_passed():
    ticket = {"id": "1"}
    result = _build_result("upload_errors", "1. step")
    result["evaluations"] = {
        "routing_accuracy": {"passed": True, "score": 5},
        "keyword_coverage": {"passed": True, "score": 0.8},
        "action_steps": {"passed": True, "score": True},
    }
    evaluator = CompositeEvaluator()
    score = evaluator.evaluate(ticket, result)
    assert score["passed"] is True


def test_safety_evaluator_flags_pii():
    ticket = {"id": "1"}
    result = _build_result("upload_errors", "my ssn is 123-45-6789")
    evaluator = SafetyEvaluator()
    score = evaluator.evaluate(ticket, result)
    assert score["passed"] is False
    assert score["flags"]["pii"] is True


def test_llm_evaluators_skip_without_client():
    """Test that LLM evaluators either skip (no client) or run (with client)."""
    ticket = {"id": "1", "issue": "test"}
    result = _build_result("upload_errors", "answer text")
    faith = LLMFaithfulnessEvaluator()
    saf = LLMSafetyEvaluator()
    score_f = faith.evaluate(ticket, result)
    score_s = saf.evaluate(ticket, result)

    # If client is available (OPENAI_API_KEY set), evaluators will run
    # If not available, they should skip
    # In either case, check they return valid scores
    assert isinstance(score_f["passed"], bool)
    assert "reasoning" in score_f
    assert isinstance(score_s["passed"], bool)
    assert "reasoning" in score_s
