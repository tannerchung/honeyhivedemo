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
    result = _build_result("upload_errors", "404 path https")
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
    ticket = {"id": "1", "issue": "test"}
    result = _build_result("upload_errors", "answer text")
    faith = LLMFaithfulnessEvaluator()
    saf = LLMSafetyEvaluator()
    score_f = faith.evaluate(ticket, result)
    score_s = saf.evaluate(ticket, result)
    assert score_f["passed"] is False
    assert "skipped" in score_f["reasoning"].lower()
    assert score_s["passed"] is False
    assert "skipped" in score_s["reasoning"].lower()
