"""
CLI entrypoint for the HoneyHive customer support demo.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from agents.support_agent import CustomerSupportAgent
from data import MOCK_TICKETS
from evaluators import (
    ActionStepsEvaluator,
    CompositeEvaluator,
    KeywordEvaluator,
    RoutingEvaluator,
)
from utils.exporters import export_to_honeyhive_sdk, export_to_json


def init_honeyhive_tracer(logger=None) -> None:
    """
    Initialize HoneyHive tracer if SDK and API key are available.
    """
    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")
    source = os.getenv("HONEYHIVE_SOURCE", "dev")
    session_name = os.getenv("HONEYHIVE_SESSION", "Demo Session")
    if not api_key:
        return
    try:
        from honeyhive import HoneyHiveTracer
    except Exception as err:
        if logger:
            logger.warning("HoneyHive SDK not available", extra={"error": str(err)})
        return
    try:
        HoneyHiveTracer.init(api_key=api_key, project=project, source=source, session_name=session_name)
        if logger:
            logger.info("HoneyHive tracer initialized", extra={"project": project, "source": source})
    except Exception as err:
        if logger:
            logger.warning("HoneyHive tracer init failed", extra={"error": str(err)})


def run_pipeline(version: str, offline: bool = False, logger=None, provider: str = "anthropic") -> List[Dict[str, Any]]:
    agent = CustomerSupportAgent(version=version, use_llm=not offline, logger=logger, provider=provider)
    evaluators = [
        RoutingEvaluator(),
        KeywordEvaluator(),
        ActionStepsEvaluator(),
        CompositeEvaluator(),
    ]

    results: List[Dict[str, Any]] = []
    for ticket in MOCK_TICKETS:
        result = agent.process_ticket(ticket)
        result["evaluations"] = {}
        for evaluator in evaluators:
            score = evaluator.evaluate(ticket, result)
            result["evaluations"][evaluator.name] = score
        results.append(result)
    return results


def print_summary(results: List[Dict[str, Any]]) -> None:
    total = len(results)
    passed = sum(
        1
        for r in results
        if r.get("evaluations", {}).get("composite", {}).get("passed")
    )
    print(f"Processed {total} tickets | passed: {passed} | failed: {total - passed}")


def evaluate_file(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    results = payload.get("results", [])
    print_summary(results)
    return results


def compare_runs(path_a: str, path_b: str) -> None:
    def load_summary(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("summary", {})

    a_sum = load_summary(path_a)
    b_sum = load_summary(path_b)
    print("Comparison (A -> B):")
    for key in ["passed", "failed"]:
        if key in a_sum and key in b_sum:
            print(f"{key}: {a_sum[key]} -> {b_sum[key]}")
    for metric, value in (b_sum.get("metrics") or {}).items():
        prev = (a_sum.get("metrics") or {}).get(metric)
        print(f"{metric}: {prev} -> {value}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="HoneyHive support agent demo")
    parser.add_argument("--run", action="store_true", help="Run pipeline on mock tickets")
    parser.add_argument("--version", default="v1", help="Version tag for the run")
    parser.add_argument("--offline", action="store_true", help="Force heuristic mode, no LLM calls")
    parser.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic", help="LLM provider")
    parser.add_argument("--export", action="store_true", help="Export results to JSON")
    parser.add_argument("--output", default="results.json", help="Export file name")
    parser.add_argument("--evaluate", help="Evaluate an existing results JSON")
    parser.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"), help="Compare two runs")
    parser.add_argument(
        "--send-to-honeyhive",
        dest="send_to_honeyhive",
        action="store_true",
        help="Attempt sending results to HoneyHive SDK",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to console and logs/run.log")
    args = parser.parse_args()

    logger = None
    if args.debug:
        import logging
        import os

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

    # Initialize HoneyHive tracing if configured
    init_honeyhive_tracer(logger=logger)

    results: List[Dict[str, Any]] = []

    if args.run:
        results = run_pipeline(version=args.version, offline=args.offline, logger=logger, provider=args.provider)
        print_summary(results)

    if args.export and results:
        export_to_json(results, filename=args.output)
        print(f"Exported results to {args.output}")
    elif args.export and not results:
        # If user only passes --export, try exporting last run file if present
        if os.path.exists(args.output):
            print(f"Results already exist at {args.output}")
        else:
            print("No results to export. Run with --run first.")

    if args.evaluate:
        evaluate_file(args.evaluate)

    if args.compare:
        compare_runs(args.compare[0], args.compare[1])

    if args.send_to_honeyhive and results:
        resp = export_to_honeyhive_sdk(results)
        print(f"HoneyHive SDK export: {resp}")
    elif args.send_to_honeyhive and not results:
        print("No in-memory results to send; run with --run first.")


if __name__ == "__main__":
    main()
