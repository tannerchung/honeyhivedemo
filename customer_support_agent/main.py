"""
CLI entrypoint for the HoneyHive customer support demo.

This module provides the command-line interface for running the customer support
agent demo. It supports multiple modes of operation:
- Standard pipeline execution with session-based tracing
- HoneyHive experiment creation with run tracking
- Result export to JSON
- Evaluation of existing result files
- Run comparison for A/B testing

The CLI handles:
- Environment configuration loading
- HoneyHive tracer initialization
- Agent instantiation and execution
- Evaluator configuration and execution
- Results export and presentation

Usage:
    # Run agent on mock dataset with HoneyHive tracing
    python -m customer_support_agent.main --run

    # Run with experiment tracking
    python -m customer_support_agent.main --run --experiment

    # Run in offline mode (heuristic only, no LLM calls)
    python -m customer_support_agent.main --run --offline

    # Run with OpenAI instead of Anthropic
    python -m customer_support_agent.main --run --provider openai

    # Export results to JSON
    python -m customer_support_agent.main --run --export --output results.json

    # Evaluate existing results
    python -m customer_support_agent.main --evaluate results.json

    # Compare two runs
    python -m customer_support_agent.main --compare run1.json run2.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from typing import Any, Dict, List

# Initialize environment configuration BEFORE any SDK imports
# This ensures OTLP endpoints are set before auto-initialization occurs
from utils.config import load_config
from utils.honeyhive_init import ensure_otlp_endpoint_set

# Load configuration and ensure OTLP endpoint is set
ensure_otlp_endpoint_set()
config = load_config()

# Now safe to import SDKs and other modules
from agents.support_agent import CustomerSupportAgent
from data.datasets import load_dataset
from evaluators import (
    ActionStepsEvaluator,
    CompositeEvaluator,
    FormatEvaluator,
    LLMFaithfulnessEvaluator,
    LLMSafetyEvaluator,
    KeywordEvaluator,
    RoutingEvaluator,
    SafetyEvaluator,
)
from utils.exporters import export_to_honeyhive_sdk, export_to_json, create_experiment_run
from utils.honeyhive_experiment import run_honeyhive_experiment
from utils.honeyhive_init import init_honeyhive_tracer


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configure application logging.

    Sets up logging to both console and file when debug mode is enabled.
    Log files are written to logs/run.log.

    Args:
        debug: Whether to enable debug-level logging

    Returns:
        logging.Logger: Configured logger instance

    Note:
        Creates logs/ directory if it doesn't exist.
    """
    if debug:
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("logs/run.log", encoding="utf-8"),
            ],
        )
        logger = logging.getLogger("customer_support_demo")
        logger.debug("Debug logging enabled")
        return logger
    return logging.getLogger("customer_support_demo")


def create_evaluators() -> List[Any]:
    """
    Create and configure all evaluators for the pipeline.

    Instantiates the full suite of evaluators used to assess agent performance:
    - RoutingEvaluator: Checks if category prediction matches ground truth
    - KeywordEvaluator: Verifies expected keywords appear in response
    - ActionStepsEvaluator: Ensures response has numbered action steps
    - FormatEvaluator: Validates response format and structure
    - SafetyEvaluator: Checks safety flags (PII, toxicity)
    - LLMFaithfulnessEvaluator: LLM-based check for hallucinations
    - LLMSafetyEvaluator: LLM-based safety assessment
    - CompositeEvaluator: Combines all evaluator results

    Returns:
        list: List of evaluator instances

    Note:
        LLM-based evaluators (LLMFaithfulnessEvaluator, LLMSafetyEvaluator)
        require API keys to function. They will gracefully degrade if keys
        are not available.
    """
    return [
        RoutingEvaluator(),
        KeywordEvaluator(),
        ActionStepsEvaluator(),
        FormatEvaluator(),
        SafetyEvaluator(),
        LLMFaithfulnessEvaluator(),
        LLMSafetyEvaluator(),
        CompositeEvaluator(),
    ]


def run_pipeline(
    version: str,
    offline: bool = False,
    logger: logging.Logger | None = None,
    provider: str = "anthropic",
    dataset_name: str = "mock",
    run_id: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Execute the customer support agent pipeline on a dataset.

    This function runs the agent on all datapoints in the specified dataset,
    evaluates the results, and returns comprehensive output including:
    - Agent predictions (category, response)
    - Evaluation scores from all evaluators
    - Trace data for observability
    - Token usage statistics

    The pipeline flow:
    1. Load dataset (mock tickets with ground truth)
    2. For each ticket:
       a. Process through agent (route → retrieve → generate)
       b. Evaluate results with all evaluators
       c. Attach evaluations to trace
    3. Return all results

    Args:
        version: Version tag for experiment tracking (e.g., "v1", "v2")
        offline: If True, force heuristic mode (no LLM calls)
        logger: Optional logger for debugging
        provider: LLM provider to use ("anthropic" or "openai")
        dataset_name: Name of dataset to load (default: "mock")
        run_id: Optional run identifier (generated if not provided)

    Returns:
        list: List of result dicts, one per ticket, each containing:
            - ticket_id: Ticket identifier
            - input: Original ticket data
            - output: Agent predictions (category, answer, steps)
            - evaluations: Dict of evaluation scores
            - trace: Trace data for observability
            - dataset: Dataset name

    Example:
        >>> results = run_pipeline(
        ...     version="v1",
        ...     provider="anthropic",
        ...     dataset_name="mock"
        ... )
        >>> print(f"Processed {len(results)} tickets")
    """
    # Create agent with specified configuration
    agent = CustomerSupportAgent(
        version=version,
        prompt_version=version,
        use_llm=not offline,  # Force heuristic mode if offline=True
        logger=logger,
        provider=provider,
    )

    # Create all evaluators
    evaluators = create_evaluators()

    # Load dataset
    datapoints = load_dataset(dataset_name)

    # Generate run ID if not provided
    run_id = run_id or str(uuid.uuid4())

    # Process each datapoint
    results: List[Dict[str, Any]] = []
    for dp in datapoints:
        # Build ticket from datapoint
        ticket = {
            "id": dp["id"],
            "customer": dp.get("customer"),
            "issue": dp["issue"]
        }

        # Process ticket through agent pipeline
        result = agent.process_ticket(
            ticket,
            run_id=run_id,
            datapoint_id=dp["id"],
            ground_truth=dp.get("ground_truth"),
        )

        # Run all evaluators on the result
        result["evaluations"] = {}
        for evaluator in evaluators:
            score = evaluator.evaluate(dp, result)
            result["evaluations"][evaluator.name] = score

        # Attach evaluations to trace metadata for HoneyHive UI
        result["trace"]["evaluations"] = result["evaluations"]

        # Add dataset name to result
        result["dataset"] = dataset_name

        results.append(result)

    return results


def print_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print a summary of pipeline results.

    Displays high-level statistics about the run:
    - Total tickets processed
    - Number that passed composite evaluation
    - Number that failed

    Args:
        results: List of result dicts from run_pipeline

    Example:
        >>> results = run_pipeline(version="v1")
        >>> print_summary(results)
        Processed 10 tickets | passed: 7 | failed: 3
    """
    total = len(results)
    passed = sum(
        1
        for r in results
        if r.get("evaluations", {}).get("composite", {}).get("passed")
    )
    print(f"Processed {total} tickets | passed: {passed} | failed: {total - passed}")


def evaluate_file(path: str) -> List[Dict[str, Any]]:
    """
    Load and evaluate results from a JSON file.

    Reads a previously exported results file and prints summary statistics.
    Useful for reviewing past runs without re-executing the pipeline.

    Args:
        path: Path to results JSON file

    Returns:
        list: List of result dicts from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    results = payload.get("results", [])
    print_summary(results)

    return results


def compare_runs(path_a: str, path_b: str) -> None:
    """
    Compare two result files for A/B testing.

    Loads two results files and prints a comparison of their summary metrics,
    including changes in pass/fail counts and individual metric scores.

    Args:
        path_a: Path to first results file (baseline)
        path_b: Path to second results file (comparison)

    Example:
        >>> compare_runs("baseline.json", "experiment.json")
        Comparison (A -> B):
        passed: 7 -> 9
        failed: 3 -> 1
        routing_accuracy: 0.85 -> 0.92
    """
    def load_summary(path: str) -> Dict[str, Any]:
        """Load summary section from results file."""
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("summary", {})

    # Load both summaries
    a_sum = load_summary(path_a)
    b_sum = load_summary(path_b)

    # Print comparison
    print("Comparison (A -> B):")

    # Compare pass/fail counts
    for key in ["passed", "failed"]:
        if key in a_sum and key in b_sum:
            print(f"{key}: {a_sum[key]} -> {b_sum[key]}")

    # Compare individual metrics
    for metric, value in (b_sum.get("metrics") or {}).items():
        prev = (a_sum.get("metrics") or {}).get(metric)
        print(f"{metric}: {prev} -> {value}")


def run_experiment_mode(
    args: argparse.Namespace,
    logger: logging.Logger | None,
) -> None:
    """
    Run HoneyHive experiment mode.

    Creates a HoneyHive experiment entry with run tracking, which appears
    in the HoneyHive UI Experiments tab. This is separate from session-based
    tracing and provides:
    - Experiment grouping and organization
    - Run comparison in UI
    - Dataset integration
    - Suite-based organization

    Args:
        args: Parsed command-line arguments
        logger: Optional logger for status messages

    Note:
        This creates both sessions (for traces) AND an experiment entry
        (for run tracking). The experiment entry makes runs visible in
        the HoneyHive Experiments tab.
    """
    print("\nRunning HoneyHive experiment...")

    # Create agent
    agent = CustomerSupportAgent(
        version=args.version,
        prompt_version=args.version,
        use_llm=not args.offline,
        logger=logger,
        provider=args.provider,
    )

    # Check for managed dataset ID (optional)
    dataset_id = config.honeyhive_dataset_id

    # Run experiment using HoneyHive SDK
    experiment_result = run_honeyhive_experiment(
        agent=agent,
        dataset_name=args.dataset,
        experiment_name=f"Customer Support Experiment - {args.version}",
        run_id=args.run_id,
        suite="Customer Support Agent",  # Group experiments in suite
        dataset_id=dataset_id,  # Use managed dataset if available
    )

    # Display results
    if experiment_result.get("success"):
        print(f"✓ HoneyHive experiment completed successfully")

        # Display metadata if available
        result_obj = experiment_result.get("result")
        if result_obj:
            try:
                # Try to extract useful info from result object
                if hasattr(result_obj, '__dict__'):
                    result_dict = result_obj.__dict__
                    if 'status' in result_dict:
                        print(f"  Status: {result_dict['status']}")

                print(f"  Suite: Customer Support Agent")

                if dataset_id:
                    print(f"  Dataset: {dataset_id} (managed)")
                else:
                    print(f"  Dataset: inline (10 test cases)")
            except Exception:
                # Ignore errors in metadata extraction
                pass

        print(f"  Check the Experiments tab in HoneyHive UI")
    else:
        print(f"✗ HoneyHive experiment failed: {experiment_result.get('reason')}")


def main() -> None:
    """
    Main CLI entrypoint.

    Parses command-line arguments and executes the requested operation:
    - --run: Execute pipeline on dataset
    - --experiment: Create HoneyHive experiment (with --run)
    - --export: Export results to JSON
    - --evaluate: Evaluate existing results file
    - --compare: Compare two results files
    - --send-to-honeyhive: Send results via SDK (legacy)

    The function handles:
    1. Argument parsing
    2. Logging setup (if --debug)
    3. HoneyHive tracer initialization
    4. Pipeline execution
    5. Experiment creation (if --experiment)
    6. Results export (if --export)
    7. File evaluation (if --evaluate)
    8. Run comparison (if --compare)

    Command-line Arguments:
        --run: Run pipeline on mock tickets
        --version: Version tag for the run (default: "v1")
        --offline: Force heuristic mode, no LLM calls
        --provider: LLM provider ("anthropic" or "openai")
        --dataset: Dataset name (default: "mock")
        --export: Export results to JSON
        --output: Export filename (default: "results.json")
        --run-id: Run identifier for experiment tracking
        --evaluate: Evaluate an existing results JSON file
        --compare: Compare two result files
        --send-to-honeyhive: Send results to HoneyHive SDK (legacy)
        --experiment: Run HoneyHive experiment (creates Experiment entry)
        --debug: Enable debug logging to console and logs/run.log

    Examples:
        # Basic run with tracing
        python -m customer_support_agent.main --run

        # Run experiment with export
        python -m customer_support_agent.main --run --experiment --export

        # Offline mode (no API calls)
        python -m customer_support_agent.main --run --offline

        # OpenAI provider
        python -m customer_support_agent.main --run --provider openai

        # Evaluate existing results
        python -m customer_support_agent.main --evaluate results.json

        # Compare two runs
        python -m customer_support_agent.main --compare run1.json run2.json
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="HoneyHive customer support agent demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,  # Use module docstring as epilog
    )

    # Run mode arguments
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run pipeline on mock tickets",
    )
    parser.add_argument(
        "--version",
        default="v1",
        help="Version tag for the run (default: v1)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force heuristic mode, no LLM calls",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--dataset",
        default="mock",
        help="Dataset name (default: mock)",
    )

    # Export arguments
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to JSON",
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Export filename (default: results.json)",
    )
    parser.add_argument(
        "--run-id",
        help="Run identifier for experiment tracking",
    )

    # Evaluation arguments
    parser.add_argument(
        "--evaluate",
        help="Evaluate an existing results JSON file",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Compare two result files for A/B testing",
    )

    # HoneyHive arguments
    parser.add_argument(
        "--send-to-honeyhive",
        dest="send_to_honeyhive",
        action="store_true",
        help="Send results to HoneyHive SDK (legacy - traces auto-sent)",
    )
    parser.add_argument(
        "--experiment",
        action="store_true",
        help="Run HoneyHive experiment (creates Experiment entry with run_id)",
    )

    # Debug argument
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to console and logs/run.log",
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(debug=args.debug)

    # Initialize HoneyHive tracing if configured
    # This sets up the tracer for session-based tracing
    if config.has_honeyhive_config():
        init_honeyhive_tracer(logger=logger)
    else:
        logger.info("Running in local mode without HoneyHive tracing")

    # Storage for results
    results: List[Dict[str, Any]] = []

    # Execute requested operation
    if args.run:
        # If running experiment, skip the standard pipeline to avoid duplicate processing
        if not args.experiment:
            # Run standard pipeline with session-based tracing (sessions only)
            results = run_pipeline(
                version=args.version,
                offline=args.offline,
                logger=logger,
                provider=args.provider,
                dataset_name=args.dataset,
                run_id=args.run_id,
            )
            print_summary(results)

        # Run HoneyHive experiment (creates both sessions AND experiment)
        if args.experiment:
            run_experiment_mode(args, logger)

    # Export results to JSON
    if args.export and results:
        export_to_json(results, filename=args.output)
        print(f"Exported results to {args.output}")

        # Also create experiment run entry (legacy)
        exp_resp = create_experiment_run(results)
        if exp_resp.get("created"):
            print(f"HoneyHive experiment/run logged: {exp_resp}")
        else:
            print(f"HoneyHive experiment not logged: {exp_resp}")

    elif args.export and not results:
        # User passed --export without --run
        if os.path.exists(args.output):
            print(f"Results already exist at {args.output}")
        else:
            print("No results to export. Run with --run first.")

    # Evaluate existing results file
    if args.evaluate:
        evaluate_file(args.evaluate)

    # Compare two results files
    if args.compare:
        compare_runs(args.compare[0], args.compare[1])

    # Send results to HoneyHive SDK (legacy)
    if args.send_to_honeyhive and results:
        resp = export_to_honeyhive_sdk(results)
        print(f"HoneyHive SDK export: {resp}")
    elif args.send_to_honeyhive and not results:
        print("No in-memory results to send; run with --run first.")


if __name__ == "__main__":
    main()
