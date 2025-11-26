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
                return 0
            passed = expected == predicted
            score = 1 if passed else 0
            return score
        except Exception as e:
            return 0

    @evaluator()
    def keyword_coverage(outputs, inputs, ground_truths):
        """Check if response contains expected keywords."""
        try:
            expected_keywords = ground_truths.get("expected_keywords", [])
            # Try both 'response' and 'answer' keys
            response = outputs.get("response") or outputs.get("answer", "")
            response = response.lower() if isinstance(response, str) else ""
            if not expected_keywords:
                return 100
            found_keywords = [kw for kw in expected_keywords if kw.lower() in response]
            # Convert to 0-100 scale for consistency with HoneyHive UI
            score = int((len(found_keywords) / len(expected_keywords)) * 100) if expected_keywords else 100
            return score
        except Exception as e:
            return 0

    @evaluator()
    def has_action_steps(outputs, inputs, ground_truths):
        """Check if response contains numbered action steps."""
        try:
            # Try both 'response' and 'answer' keys
            response = outputs.get("response") or outputs.get("answer", "")
            response = response if isinstance(response, str) else ""
            step_numbers = [i for i in range(1, 11) if f"{i}." in response or f"{i})" in response]
            has_steps = len(step_numbers) > 0
            score = 1 if has_steps else 0
            return score
        except Exception as e:
            return 0

    return [routing_accuracy, keyword_coverage, has_action_steps]


def run_honeyhive_experiment(
    agent,
    dataset_name: str = "mock",
    experiment_name: str = "Customer Support Experiment",
    run_id: str | None = None,
    suite: str | None = None,
    dataset_id: str | None = None,
) -> Dict[str, Any]:
    """
    Run HoneyHive experiment using evaluate() framework.
    This creates an Experiment entry with run_id visible in the UI.

    Args:
        agent: The agent to evaluate
        dataset_name: Name of dataset to load (if dataset_id not provided)
        experiment_name: Name of the experiment
        run_id: Optional run identifier
        suite: Optional suite name for grouping experiments
        dataset_id: Optional HoneyHive dataset ID (uses inline dataset if not provided)
    """
    try:
        from honeyhive import evaluate
    except ImportError:
        return {"success": False, "reason": "HoneyHive evaluate not available"}

    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")

    if not api_key:
        return {"success": False, "reason": "Missing HONEYHIVE_API_KEY"}

    # Load dataset (only if dataset_id not provided)
    dataset = None
    if not dataset_id:
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
        # Import enrich_session here to ensure it's available
        try:
            from honeyhive import enrich_session
        except ImportError:
            enrich_session = None

        # Enrich the session with ground truth BEFORE processing
        # Provide both flat fields AND nested ground_truth for compatibility with different evaluators
        if enrich_session and ground_truths:
            feedback_data = dict(ground_truths)  # Copy all fields at flat level
            feedback_data["ground_truth"] = ground_truths  # Also nest under ground_truth key
            enrich_session(feedback=feedback_data)

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
        # Use "answer" from agent output, but provide as both "response" and "answer" for compatibility
        answer = result.get("output", {}).get("answer", "")
        output_dict = result.get("output", {})
        return {
            "category": output_dict.get("category"),
            "confidence": output_dict.get("confidence"),
            "reasoning": output_dict.get("reasoning"),
            "response": answer,  # For keyword_coverage and has_action_steps evaluators
            "answer": answer,    # For compatibility
        }

    # Create evaluators
    evaluators = create_honeyhive_evaluators()

    try:
        # Build evaluate() parameters
        eval_params = {
            "function": function_to_evaluate,
            "api_key": api_key,
            "project": project,
            "name": experiment_name,
            "evaluators": evaluators,
        }

        # Add suite if provided (Enhancement #1: Suite parameter)
        if suite:
            eval_params["suite"] = suite

        # Use dataset_id if provided, otherwise inline dataset (Enhancement #4: Dataset ID)
        if dataset_id:
            eval_params["dataset_id"] = dataset_id
        else:
            eval_params["dataset"] = dataset

        # Run experiment
        result = evaluate(**eval_params)

        # Enhancement #2 & #5: Capture and display return value
        return {
            "success": True,
            "result": result,
            # Extract useful metadata if available
            "metadata": {
                "suite": suite,
                "dataset_id": dataset_id if dataset_id else "inline",
                "experiment_name": experiment_name,
            }
        }
    except Exception as err:
        return {"success": False, "reason": str(err)}
