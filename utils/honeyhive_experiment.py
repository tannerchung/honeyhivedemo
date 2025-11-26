"""
HoneyHive experiment integration using the evaluate() framework.

This module provides integration with HoneyHive's experiment tracking system using
the evaluate() SDK method. It runs alongside session-based tracing to provide
comprehensive experiment tracking and comparison.

Key responsibilities:
- Create HoneyHive-compatible evaluators using @evaluator decorator
- Run experiments via HoneyHive evaluate() framework
- Handle both inline and managed datasets
- Support suite-based experiment organization
- Enrich sessions with ground truth for evaluation

The evaluate() framework provides:
- Experiment entries visible in HoneyHive UI Experiments tab
- Run comparison and A/B testing capabilities
- Dataset integration (inline or managed)
- Suite-based organization of related experiments
- Automatic metric aggregation

Architecture:
    This works in parallel with session-based tracing:
    - Sessions: Individual trace entries for each ticket (via @trace decorator)
    - Experiments: Grouped runs for comparison (via evaluate() framework)

    Both are valuable:
    - Sessions provide detailed trace-level observability
    - Experiments provide high-level run comparison and metrics
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from data.datasets import load_dataset


def create_honeyhive_evaluators() -> List[Any]:
    """
    Create HoneyHive-compatible evaluators using the @evaluator decorator.

    These evaluators work with the HoneyHive evaluate() framework for experiment
    tracking. They're separate from the local evaluators in evaluators/ module
    because they have a different signature that matches HoneyHive's expectations.

    Returns:
        list: List of evaluator functions decorated with @evaluator, or empty list
              if HoneyHive SDK is not available

    Note:
        Evaluators receive (outputs, inputs, ground_truths) args from the framework.
        They must return numeric scores that HoneyHive can aggregate and display.

    Evaluators created:
        - routing_accuracy: Binary score (0 or 1) for category match
        - keyword_coverage: 0-100 score for keyword presence
        - has_action_steps: Binary score (0 or 1) for numbered steps

    Example:
        >>> evaluators = create_honeyhive_evaluators()
        >>> if evaluators:
        ...     print(f"Created {len(evaluators)} evaluators")
    """
    try:
        from honeyhive import evaluator
    except ImportError:
        # HoneyHive SDK not available
        return []

    @evaluator()
    def routing_accuracy(outputs, inputs, ground_truths):
        """
        Check if the routed category matches ground truth.

        This evaluator compares the agent's predicted category against the
        expected category from ground truth. It returns a binary score:
        1 for correct routing, 0 for incorrect.

        Args:
            outputs: Dict with agent outputs, should contain "category" key
            inputs: Dict with ticket inputs (not used for this eval)
            ground_truths: Dict with expected values, should contain "expected_category"

        Returns:
            int: 1 if categories match, 0 otherwise

        Note:
            Returns 0 if expected_category or predicted category is missing,
            which is safer than failing the entire evaluation.
        """
        try:
            expected = ground_truths.get("expected_category")
            predicted = outputs.get("category")

            # Missing data means we can't evaluate
            if not expected or not predicted:
                return 0

            # Binary score: exact match or not
            passed = expected == predicted
            score = 1 if passed else 0

            return score

        except Exception as e:
            # Fail gracefully - don't break the entire experiment
            return 0

    @evaluator()
    def keyword_coverage(outputs, inputs, ground_truths):
        """
        Check if response contains expected keywords.

        This evaluator verifies that the agent's response includes the keywords
        that should be present based on ground truth. It returns a percentage
        score (0-100) representing the fraction of expected keywords found.

        Args:
            outputs: Dict with agent outputs, should contain "response" or "answer"
            inputs: Dict with ticket inputs (not used for this eval)
            ground_truths: Dict with "expected_keywords" list

        Returns:
            int: Percentage (0-100) of expected keywords found

        Note:
            - Returns 100 if no expected keywords (vacuously true)
            - Case-insensitive keyword matching
            - Tries both "response" and "answer" keys for compatibility
        """
        try:
            expected_keywords = ground_truths.get("expected_keywords", [])

            # Try both 'response' and 'answer' keys for compatibility
            # Different parts of the pipeline may use different keys
            response = outputs.get("response") or outputs.get("answer", "")
            response = response.lower() if isinstance(response, str) else ""

            # If no keywords expected, score is 100 (vacuously true)
            if not expected_keywords:
                return 100

            # Count how many expected keywords are found
            found_keywords = [
                kw for kw in expected_keywords
                if kw.lower() in response
            ]

            # Convert to 0-100 scale for consistency with HoneyHive UI
            score = int((len(found_keywords) / len(expected_keywords)) * 100) if expected_keywords else 100

            return score

        except Exception as e:
            # Fail gracefully
            return 0

    @evaluator()
    def has_action_steps(outputs, inputs, ground_truths):
        """
        Check if response contains numbered action steps.

        This evaluator verifies that the agent's response is formatted with
        numbered steps (1., 2., 3., etc.). This is important for customer
        support responses to be actionable and easy to follow.

        Args:
            outputs: Dict with agent outputs, should contain "response" or "answer"
            inputs: Dict with ticket inputs (not used for this eval)
            ground_truths: Dict with ground truth data (not used for this eval)

        Returns:
            int: 1 if response contains numbered steps, 0 otherwise

        Note:
            - Looks for patterns like "1.", "2.", "3)" etc.
            - Checks numbers 1-10 (supports up to 10 steps)
            - Tries both "response" and "answer" keys for compatibility
        """
        try:
            # Try both 'response' and 'answer' keys
            response = outputs.get("response") or outputs.get("answer", "")
            response = response if isinstance(response, str) else ""

            # Look for numbered steps (1. or 1))
            step_numbers = [
                i for i in range(1, 11)
                if f"{i}." in response or f"{i})" in response
            ]

            # Binary score: has steps or doesn't
            has_steps = len(step_numbers) > 0
            score = 1 if has_steps else 0

            return score

        except Exception as e:
            # Fail gracefully
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
    Run HoneyHive experiment using the evaluate() framework.

    This function creates an Experiment entry in HoneyHive with a visible run_id
    that appears in the Experiments tab of the UI. It processes the entire dataset
    through the agent, evaluates results, and tracks everything in HoneyHive.

    The evaluate() framework provides:
    - Experiment entries in the HoneyHive UI
    - Run comparison for A/B testing
    - Automatic metric aggregation
    - Suite-based organization
    - Integration with managed datasets

    Args:
        agent: CustomerSupportAgent instance to evaluate
        dataset_name: Name of local dataset to load (used if dataset_id not provided)
        experiment_name: Name for the experiment (appears in HoneyHive UI)
        run_id: Optional run identifier (passed to agent.process_ticket)
        suite: Optional suite name for grouping related experiments
        dataset_id: Optional HoneyHive managed dataset ID (uses inline data if not provided)

    Returns:
        dict: Result dictionary with keys:
            - success: bool indicating if experiment completed
            - reason: str error message if success=False
            - result: Return value from evaluate() if success=True
            - metadata: Dict with experiment metadata

    Note:
        Ground truth enrichment happens at multiple levels:
        - Session level (enrich_session) for UI evaluators
        - Span level (enrich_span) for span-based evaluators
        - Instance level (agent._ground_truth) for method access

        This redundancy ensures evaluators can access ground truth regardless
        of where they hook into the trace data.

    Example:
        >>> from agents.support_agent import CustomerSupportAgent
        >>> agent = CustomerSupportAgent()
        >>> result = run_honeyhive_experiment(
        ...     agent=agent,
        ...     experiment_name="My Experiment",
        ...     suite="Customer Support",
        ... )
        >>> if result["success"]:
        ...     print("Experiment completed successfully")
    """
    # Try to import HoneyHive evaluate function
    try:
        from honeyhive import evaluate
    except ImportError:
        return {
            "success": False,
            "reason": "HoneyHive SDK not installed (pip install honeyhive)",
        }

    # Load configuration from environment
    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")

    if not api_key:
        return {
            "success": False,
            "reason": "Missing HONEYHIVE_API_KEY environment variable",
        }

    # Load dataset (only if dataset_id not provided)
    # When using managed datasets, we don't need to load local data
    dataset = None
    if not dataset_id:
        datapoints = load_dataset(dataset_name)

        # Convert to HoneyHive format: list of dicts with "inputs" and "ground_truths"
        # This is the format expected by the evaluate() framework
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

    # Define the function to evaluate
    def function_to_evaluate(inputs, ground_truths):
        """
        Process a single ticket through the agent.

        This function is called by the evaluate() framework for each datapoint.
        It handles ground truth enrichment, agent execution, and output formatting.

        Args:
            inputs: Dict with ticket data (id, customer, issue)
            ground_truths: Dict with expected values for evaluation

        Returns:
            dict: Outputs dict with category, confidence, reasoning, response, answer

        Note:
            Ground truth is enriched BEFORE processing to ensure evaluators can
            access it from session metadata. The enrichment is defensive - it
            handles missing enrich_session gracefully for local development.
        """
        # Import enrich_session here to ensure it's available
        # This is done inside the function to handle import errors gracefully
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

        # Build ticket dict from inputs
        ticket = {
            "id": inputs["id"],
            "customer": inputs.get("customer"),
            "issue": inputs["issue"],
        }

        # Process ticket through agent pipeline
        result = agent.process_ticket(
            ticket,
            run_id=run_id,
            datapoint_id=inputs["id"],
            ground_truth=ground_truths,
        )

        # Extract the answer from agent output
        # Provide as both "response" and "answer" for evaluator compatibility
        answer = result.get("output", {}).get("answer", "")
        output_dict = result.get("output", {})

        # Return outputs in format expected by evaluators
        return {
            "category": output_dict.get("category"),
            "confidence": output_dict.get("confidence"),
            "reasoning": output_dict.get("reasoning"),
            "response": answer,  # For keyword_coverage and has_action_steps evaluators
            "answer": answer,    # For compatibility
        }

    # Create evaluators for this experiment
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

        # Add suite if provided
        # Suites help organize related experiments in the HoneyHive UI
        if suite:
            eval_params["suite"] = suite

        # Use dataset_id if provided, otherwise inline dataset
        # Managed datasets are stored in HoneyHive and can be reused across runs
        # Inline datasets are passed directly and are ephemeral
        if dataset_id:
            eval_params["dataset_id"] = dataset_id
        else:
            eval_params["dataset"] = dataset

        # Run experiment via evaluate() framework
        # This creates an experiment entry in HoneyHive with the run_id
        result = evaluate(**eval_params)

        # Return success with result object and metadata
        return {
            "success": True,
            "result": result,
            # Extract useful metadata for display
            "metadata": {
                "suite": suite,
                "dataset_id": dataset_id if dataset_id else "inline",
                "experiment_name": experiment_name,
            }
        }

    except Exception as err:
        # Experiment failed - return error details
        return {
            "success": False,
            "reason": str(err),
        }
