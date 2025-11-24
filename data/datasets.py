"""
Datasets for experiments. Currently wraps mock tickets and ground truth labels.
"""

from __future__ import annotations

from typing import List, Dict, Any

from .mock_tickets import MOCK_TICKETS
from .ground_truth import GROUND_TRUTH


def load_dataset(name: str = "mock") -> List[Dict[str, Any]]:
    """
    Returns a list of datapoints with ground truth annotations.
    """
    if name != "mock":
        raise ValueError(f"Unknown dataset: {name}")
    datapoints: List[Dict[str, Any]] = []
    for ticket in MOCK_TICKETS:
        gt = GROUND_TRUTH.get(ticket["id"], {})
        datapoints.append(
            {
                "id": ticket["id"],
                "customer": ticket["customer"],
                "issue": ticket["issue"],
                "ground_truth": {
                    "expected_category": gt.get("expected_category"),
                    "expected_keywords": gt.get("expected_keywords", []),
                    "expected_tone": gt.get("expected_tone"),
                },
            }
        )
    return datapoints
