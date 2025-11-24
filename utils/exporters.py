"""
Export helpers for HoneyHive-compatible JSON payloads.
"""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from typing import Any, Dict, List


def _collect_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    routing_scores = []
    keyword_scores = []
    action_flags = []

    for result in results:
        evaluations = result.get("evaluations", {})
        if "routing_accuracy" in evaluations:
            routing_scores.append(evaluations["routing_accuracy"]["score"])
        if "keyword_coverage" in evaluations:
            keyword_scores.append(evaluations["keyword_coverage"]["score"])
        if "action_steps" in evaluations:
            action_flags.append(bool(evaluations["action_steps"]["score"]))

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

    # Simple bottleneck heuristic: lowest metric is bottleneck
    if summary:
        bottleneck_metric = min(summary, key=summary.get)
        summary["bottleneck"] = bottleneck_metric

    return summary


def export_to_json(results: List[Dict[str, Any]], filename: str = "results.json") -> Dict[str, Any]:
    """
    Export results in HoneyHive-compatible JSON format.
    """
    total = len(results)
    passed = sum(
        1
        for result in results
        if result.get("evaluations", {}).get("composite", {}).get("passed")
    )
    summary_metrics = _collect_metrics(results)
    payload = {
        "project": "customer_support_demo",
        "run_id": str(uuid.uuid4()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "metrics": summary_metrics,
        },
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def export_to_honeyhive_sdk(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    If HoneyHive SDK is available, send traces directly.
    """
    try:
        from honeyhive import HoneyHive  # type: ignore
    except Exception:
        return {"sent": False, "reason": "HoneyHive SDK not installed"}

    client = HoneyHive(
        api_key=os.getenv("HONEYHIVE_API_KEY"),
        project=os.getenv("HONEYHIVE_PROJECT", "customer_support_demo"),
    )

    for result in results:
        client.log(result)  # type: ignore[attr-defined]

    return {"sent": True, "count": len(results)}
