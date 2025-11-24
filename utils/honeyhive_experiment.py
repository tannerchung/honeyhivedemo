"""
HoneyHive experiment integration using evaluate() framework.
Runs alongside session-based tracing for comprehensive tracking.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from data.datasets import load_dataset


def create_honeyhive_evaluators():
    """
    Create HoneyHive-compatible evaluators using the @evaluator decorator.
    These work with the evaluate() framework for experiment tracking.
    """
    try:
        from honeyhive import evaluator
    except ImportError:
        return []

    @evaluator()
    def routing_accuracy(outputs, inputs, ground_truths):
        """Check if the routed category matches ground truth."""
        try:
            expected = ground_truths.get("expected_category")
            predicted = outputs.get("category")
            if not expected or not predicted:
                return {"score": 0, "passed": False}
            passed = expected == predicted
            return {"score": 1.0 if passed else 0.0, "passed": passed}
        except Exception:
            return {"score": 0, "passed": False}

    @evaluator()
    def keyword_coverage(outputs, inputs, ground_truths):
        """Check if response contains expected keywords."""
        try:
            expected_keywords = ground_truths.get("expected_keywords", [])
            response = outputs.get("response", "").lower()
            if not expected_keywords:
                return {"score": 1.0, "passed": True}
            found = sum(1 for kw in expected_keywords if kw.lower() in response)
            score = found / len(expected_keywords) if expected_keywords else 1.0
            return {"score": score, "passed": score >= 0.5}
        except Exception:
            return {"score": 0, "passed": False}

    @evaluator()
    def has_action_steps(outputs, inputs, ground_truths):
        """Check if response contains numbered action steps."""
        try:
            response = outputs.get("response", "")
            has_steps = any(
                f"{i}." in response or f"{i})" in response
                for i in range(1, 6)
            )
            return {"score": 1.0 if has_steps else 0.0, "passed": has_steps}
        except Exception:
            return {"score": 0, "passed": False}

    return [routing_accuracy, keyword_coverage, has_action_steps]


def run_honeyhive_experiment(
    agent,
    dataset_name: str = "mock",
    experiment_name: str = "Customer Support Experiment",
    run_id: str | None = None,
) -> Dict[str, Any]:
    """
    Run HoneyHive experiment using evaluate() framework.
    This creates an Experiment entry with run_id visible in the UI.
    """
    try:
        from honeyhive import evaluate
    except ImportError:
        return {"success": False, "reason": "HoneyHive evaluate not available"}

    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")

    if not api_key:
        return {"success": False, "reason": "Missing HONEYHIVE_API_KEY"}

    # Load dataset
    datapoints = load_dataset(dataset_name)

    # Convert to HoneyHive format: list of dicts with "inputs" and "ground_truths"
    dataset = []
    for dp in datapoints:
        dataset.append({
            "inputs": {
                "id": dp["id"],
                "customer": dp.get("customer"),
                "issue": dp["issue"],
            },
            "ground_truths": dp.get("ground_truth", {}),
        })

    # Function to evaluate - takes inputs and ground_truths
    def function_to_evaluate(inputs, ground_truths):
        """Process a single ticket through the agent."""
        ticket = {
            "id": inputs["id"],
            "customer": inputs.get("customer"),
            "issue": inputs["issue"],
        }
        result = agent.process_ticket(
            ticket,
            run_id=run_id,
            datapoint_id=inputs["id"],
            ground_truth=ground_truths,
        )
        # Return the output that evaluators will receive
        return {
            "category": result.get("output", {}).get("category"),
            "response": result.get("output", {}).get("response"),
        }

    # Create evaluators
    evaluators = create_honeyhive_evaluators()

    try:
        # Run experiment
        result = evaluate(
            function=function_to_evaluate,
            api_key=api_key,
            project=project,
            name=experiment_name,
            dataset=dataset,
            evaluators=evaluators,
        )
        return {"success": True, "result": result}
    except Exception as err:
        return {"success": False, "reason": str(err)}
