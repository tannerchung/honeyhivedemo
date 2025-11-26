"""
Export helpers for HoneyHive-compatible JSON payloads.

This module provides utilities for exporting agent results to various formats:
- JSON files for local storage and analysis
- HoneyHive SDK for direct upload (legacy - traces now auto-sent)
- Experiment run creation (legacy - now handled by evaluate() framework)

The JSON export format is compatible with HoneyHive's data model and includes:
- Individual result details (predictions, evaluations, traces)
- Summary statistics (pass/fail counts, metric aggregations)
- Metadata (run_id, dataset, timestamp)

Key responsibilities:
- Collect and aggregate metrics from results
- Export results to structured JSON format
- Identify performance bottlenecks
- Provide legacy HoneyHive SDK integration (for backwards compatibility)

Note:
    With HoneyHive SDK 0.2.57+, traces are automatically sent via HoneyHiveTracer
    and experiments are created via the evaluate() framework. The export functions
    here are kept for backwards compatibility and local file-based analysis.
"""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from typing import Any, Dict, List


def _collect_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collect and aggregate metrics from evaluation results.

    This function processes evaluation scores from all results and computes
    summary statistics for each metric. It also identifies potential bottlenecks
    by finding the metric with the lowest average score.

    Args:
        results: List of result dicts from pipeline execution, each containing
                an "evaluations" dict with scores from various evaluators

    Returns:
        dict: Summary metrics containing:
            - routing_accuracy: Mean routing accuracy score (0-1)
            - keyword_coverage: Mean keyword coverage score (0-1)
            - action_steps_presence: Mean action steps presence (0-1)
            - bottleneck: Name of metric with lowest score

    Note:
        Metrics are computed only from results that have the corresponding
        evaluation. If no results have a particular metric, it defaults to 0.

    Example:
        >>> results = [
        ...     {"evaluations": {"routing_accuracy": {"score": 1.0}}},
        ...     {"evaluations": {"routing_accuracy": {"score": 0.8}}},
        ... ]
        >>> metrics = _collect_metrics(results)
        >>> print(metrics["routing_accuracy"])  # 0.9
    """
    # Collect scores for each metric across all results
    routing_scores = []
    keyword_scores = []
    action_flags = []

    for result in results:
        evaluations = result.get("evaluations", {})

        # Routing accuracy scores
        if "routing_accuracy" in evaluations:
            routing_scores.append(evaluations["routing_accuracy"]["score"])

        # Keyword coverage scores
        if "keyword_coverage" in evaluations:
            keyword_scores.append(evaluations["keyword_coverage"]["score"])

        # Action steps presence (binary)
        if "action_steps" in evaluations:
            action_flags.append(bool(evaluations["action_steps"]["score"]))

    # Compute summary statistics
    summary = {
        "routing_accuracy": round(statistics.mean(routing_scores), 3)
        if routing_scores
        else 0,
        "keyword_coverage": round(statistics.mean(keyword_scores), 3)
        if keyword_scores
        else 0,
        "action_steps_presence": round(
            sum(action_flags) / len(action_flags), 3
        )
        if action_flags
        else 0,
    }

    # Identify bottleneck: metric with lowest score
    # This helps identify which aspect of the agent needs improvement
    if summary:
        bottleneck_metric = min(summary, key=summary.get)  # type: ignore
        summary["bottleneck"] = bottleneck_metric

    return summary


def export_to_json(
    results: List[Dict[str, Any]],
    filename: str = "results.json",
) -> Dict[str, Any]:
    """
    Export results to HoneyHive-compatible JSON format.

    This function creates a comprehensive JSON file containing all results,
    summary statistics, and metadata. The format is compatible with HoneyHive's
    data model and can be:
    - Loaded for later analysis
    - Compared with other runs
    - Uploaded to HoneyHive (if using legacy import methods)

    Args:
        results: List of result dicts from pipeline execution
        filename: Output filename (default: "results.json")

    Returns:
        dict: The complete payload that was written to file, containing:
            - project: Project name
            - run_id: Run identifier
            - dataset: Dataset name
            - prompt_version: Prompt version used
            - timestamp: ISO 8601 timestamp
            - results: List of individual results
            - summary: Aggregated statistics and metrics

    Note:
        The file is written with pretty-printing (indent=2) for readability.
        All results must have the same run_id and dataset for consistency.

    Example:
        >>> results = run_pipeline(version="v1")
        >>> payload = export_to_json(results, "experiment_v1.json")
        >>> print(f"Exported {payload['summary']['total']} results")

    File Format:
        {
          "project": "customer_support_demo",
          "run_id": "abc123",
          "dataset": "mock",
          "prompt_version": "v1",
          "timestamp": "2025-01-15T10:30:00Z",
          "results": [...],
          "summary": {
            "total": 10,
            "passed": 7,
            "failed": 3,
            "metrics": {...}
          }
        }
    """
    # Calculate summary statistics
    total = len(results)
    passed = sum(
        1
        for result in results
        if result.get("evaluations", {}).get("composite", {}).get("passed")
    )

    # Collect detailed metrics
    summary_metrics = _collect_metrics(results)

    # Extract metadata from first result (all should have same run_id/dataset)
    first = results[0] if results else {}

    # Build complete payload
    payload = {
        "project": "customer_support_demo",
        "run_id": first.get("run_id") or str(uuid.uuid4()),
        "dataset": first.get("dataset", "unknown"),
        "prompt_version": first.get("prompt_version"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "metrics": summary_metrics,
        },
    }

    # Write to file with pretty printing
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def export_to_honeyhive_sdk(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Export results to HoneyHive SDK (legacy function).

    **Note: This function is kept for backwards compatibility but is no longer
    needed with HoneyHive SDK 0.2.57+.**

    In modern versions of the HoneyHive SDK, traces are automatically sent to
    the platform via the HoneyHiveTracer when the @trace decorator is used.
    There's no need to manually export traces.

    This function now simply returns a status message indicating that traces
    are being sent automatically.

    Args:
        results: List of result dicts (not used, kept for API compatibility)

    Returns:
        dict: Status dict with keys:
            - sent: Always True (traces are auto-sent)
            - count: Number of results (for reference)
            - note: Explanation that traces are auto-sent

    Example:
        >>> results = run_pipeline(version="v1")
        >>> status = export_to_honeyhive_sdk(results)
        >>> print(status["note"])
        Traces sent automatically via HoneyHiveTracer

    Historical Context:
        In earlier versions of HoneyHive SDK, traces needed to be manually
        collected and sent. This function performed that manual export.
        With SDK auto-instrumentation, manual export is obsolete.
    """
    return {
        "sent": True,
        "count": len(results),
        "note": "Traces sent automatically via HoneyHiveTracer",
    }


def create_experiment_run(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create an experiment run entry in HoneyHive (legacy function).

    **Note: This function is kept for backwards compatibility but is no longer
    the recommended approach with HoneyHive SDK 0.2.57+.**

    In modern versions of the SDK, experiment runs should be created using the
    evaluate() framework (see utils/honeyhive_experiment.py). The evaluate()
    framework provides better integration with HoneyHive's experiment tracking,
    including run comparison, metric aggregation, and UI visibility.

    This function now simply returns a status message indicating that experiment
    data is being sent via HoneyHiveTracer.

    Args:
        results: List of result dicts containing run_id

    Returns:
        dict: Status dict with keys:
            - created: Always True (for backwards compatibility)
            - run_id: Run identifier from results
            - note: Explanation that experiment data is auto-sent

    Example:
        >>> results = run_pipeline(version="v1")
        >>> status = create_experiment_run(results)
        >>> print(f"Run ID: {status['run_id']}")

    Migration Guide:
        Instead of this function, use:
        ```python
        from utils.honeyhive_experiment import run_honeyhive_experiment

        result = run_honeyhive_experiment(
            agent=agent,
            experiment_name="My Experiment",
            suite="Customer Support"
        )
        ```

    Historical Context:
        Earlier versions of the demo used manual API calls to create experiment
        entries. The evaluate() framework now handles this automatically with
        better UX and more features.
    """
    if not results:
        return {
            "created": False,
            "reason": "No results provided",
        }

    run_id = results[0].get("run_id")

    return {
        "created": True,
        "run_id": run_id,
        "note": "Experiment data sent via HoneyHiveTracer. Use evaluate() framework for full experiment tracking.",
    }
