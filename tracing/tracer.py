"""
Lightweight OpenTelemetry-style tracer for demo traces.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional


class Tracer:
    """
    Collects per-step traces with timings, inputs, and outputs.
    """

    def __init__(self):
        self.current_trace: Dict[str, Any] = {}
        self.steps: List[Dict[str, Any]] = []

    def start_trace(self, ticket_id: str, version: str | None = None) -> None:
        self.current_trace = {
            "trace_id": str(uuid.uuid4()),
            "ticket_id": ticket_id,
            "version": version,
            "start_time": time.time(),
            "steps": [],
        }
        self.steps = []

    def record_step(
        self, step_name: str, input_payload: Dict[str, Any], output_payload: Dict[str, Any]
    ) -> None:
        start = time.time()
        step_record = {
            "name": step_name,
            "input": input_payload,
            "output": output_payload,
            "start_time": start,
            "end_time": None,
            "latency_ms": None,
        }
        # In a real tracer we'd wrap around the execution; here we record after computation.
        end = time.time()
        step_record["end_time"] = end
        step_record["latency_ms"] = round((end - start) * 1000, 2)
        self.steps.append(step_record)

    def end_trace(self) -> Dict[str, Any]:
        end_time = time.time()
        self.current_trace["end_time"] = end_time
        self.current_trace["latency_ms"] = round(
            (end_time - self.current_trace["start_time"]) * 1000, 2
        )
        self.current_trace["steps"] = self.steps
        return self.current_trace
