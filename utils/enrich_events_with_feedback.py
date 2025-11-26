"""
Post-process HoneyHive experiment events to add ground truth feedback to LLM completion spans.

This script fetches event IDs from an evaluation run and adds feedback to the auto-instrumented
LLM completion events so that UI evaluators can access event.feedback.ground_truth.
"""

import os
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


def list_evaluation_runs(api_key: str, project: str) -> List[Dict[str, Any]]:
    """
    List all evaluation runs for a project.

    Args:
        api_key: HoneyHive API key
        project: HoneyHive project name

    Returns:
        List of evaluation run dictionaries
    """
    url = "https://api.honeyhive.ai/runs"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    params = {
        "project": project,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("evaluations", [])
    except Exception as e:
        print(f"Error listing runs: {e}")
        return []


def find_run_by_name(run_name: str, api_key: str, project: str) -> Optional[str]:
    """
    Find an evaluation run ID by its name.

    Args:
        run_name: Name of the evaluation run to find
        api_key: HoneyHive API key
        project: HoneyHive project name

    Returns:
        Run ID (UUID) if found, None otherwise
    """
    runs = list_evaluation_runs(api_key, project)

    # Filter by name
    matching_runs = [r for r in runs if r.get("name") == run_name]

    if not matching_runs:
        return None

    # Return the most recent (assuming they're sorted by created_at desc)
    return matching_runs[0].get("run_id")


def get_run_info(run_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch evaluation run information including event_ids.

    Args:
        run_id: HoneyHive evaluation run ID
        api_key: HoneyHive API key

    Returns:
        Run info dictionary (the 'evaluation' object) or None if error
    """
    url = f"https://api.honeyhive.ai/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Extract the 'evaluation' object from the response
        return data.get("evaluation")
    except Exception as e:
        print(f"Error fetching run {run_id}: {e}")
        return None


def get_event(event_id: str, api_key: str, project: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single event by ID.

    Args:
        event_id: HoneyHive event ID
        api_key: HoneyHive API key
        project: HoneyHive project name

    Returns:
        Event dictionary or None if error
    """
    url = f"https://api.honeyhive.ai/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    params = {
        "project": project,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching event {event_id}: {e}")
        return None


def update_event_feedback(
    event_id: str,
    feedback_data: Dict[str, Any],
    api_key: str,
    project: str,
) -> bool:
    """
    Update an event with feedback data using PUT /events endpoint.

    Args:
        event_id: HoneyHive event ID
        feedback_data: Dictionary of feedback to add to the event
        api_key: HoneyHive API key
        project: HoneyHive project name

    Returns:
        True if successful, False otherwise
    """
    url = "https://api.honeyhive.ai/events"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "event_id": event_id,
        "feedback": feedback_data,
    }

    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error updating event {event_id}: {e}")
        return False


def enrich_experiment_with_feedback(
    run_id: str,
    ground_truth_map: Dict[str, Dict[str, Any]],
    api_key: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich all LLM completion events in an experiment run with ground truth feedback.

    This function:
    1. Fetches the evaluation run info to get event_ids
    2. For each event, checks if it has a datapoint_id
    3. Looks up the ground truth for that datapoint
    4. Updates the event's feedback with ground truth

    Args:
        run_id: HoneyHive evaluation run ID (from experiments)
        ground_truth_map: Map of datapoint_id -> ground_truth data
        api_key: HoneyHive API key (defaults to env var)
        project: HoneyHive project name (defaults to env var)

    Returns:
        Dictionary with success status and statistics
    """
    api_key = api_key or os.getenv("HONEYHIVE_API_KEY")
    project = project or os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")

    if not api_key:
        return {"success": False, "error": "Missing HONEYHIVE_API_KEY"}

    try:
        # Fetch run information
        print(f"Fetching run info for run_id: {run_id}")
        run_info = get_run_info(run_id, api_key)

        if not run_info:
            return {"success": False, "error": f"Could not fetch run {run_id}"}

        # Get event IDs from the run
        event_ids = run_info.get("event_ids", [])
        datapoint_ids = run_info.get("datapoint_ids", [])

        print(f"Found {len(event_ids)} events in run")
        print(f"Found {len(datapoint_ids)} datapoints in run")

        stats = {
            "total_events": len(event_ids),
            "events_checked": 0,
            "events_updated": 0,
            "events_skipped": 0,
            "events_failed": 0,
        }

        # Process each event
        for event_id in event_ids:
            stats["events_checked"] += 1

            # Fetch the event to get its metadata and inputs
            event = get_event(event_id, api_key, project)

            if not event:
                print(f"  Could not fetch event {event_id}")
                stats["events_failed"] += 1
                continue

            # Try to find our original issue ID in multiple places
            # 1. First try inputs.inputs.id (when using evaluate() framework)
            original_id = event.get("inputs", {}).get("inputs", {}).get("id")

            # 2. If not found, try inputs.id (direct structure)
            if not original_id:
                original_id = event.get("inputs", {}).get("id")

            # 3. Convert to our ground truth key format (issue-{id})
            if original_id:
                datapoint_id = f"issue-{original_id}"
            else:
                datapoint_id = None

            if not datapoint_id:
                print(f"  Event {event_id}: No datapoint_id in metadata or inputs")
                stats["events_skipped"] += 1
                continue

            # Check if we have ground truth for this datapoint
            if datapoint_id not in ground_truth_map:
                print(f"  Event {event_id}: datapoint_id '{datapoint_id}' not in ground truth map")
                stats["events_skipped"] += 1
                continue

            # Get ground truth for this datapoint
            ground_truth = ground_truth_map[datapoint_id]

            # Prepare feedback data (both flat and nested for compatibility)
            feedback_data = dict(ground_truth)
            feedback_data["ground_truth"] = ground_truth

            # Update the event
            print(f"  Updating event {event_id} with ground truth for datapoint {datapoint_id}")
            if update_event_feedback(event_id, feedback_data, api_key, project):
                stats["events_updated"] += 1
            else:
                stats["events_failed"] += 1

        return {
            "success": True,
            "stats": stats,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def enrich_experiment_from_dataset(
    run_id: str,
    dataset_name: str = "mock",
    api_key: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich experiment events by loading ground truth from the dataset.

    Args:
        run_id: HoneyHive run ID
        dataset_name: Dataset name to load ground truth from
        api_key: HoneyHive API key (defaults to env var)
        project: HoneyHive project name (defaults to env var)

    Returns:
        Dictionary with success status and statistics
    """
    from data.datasets import load_dataset

    # Load dataset to get ground truth
    datapoints = load_dataset(dataset_name)

    # Create ground truth map with multiple key formats for compatibility
    # - "issue-{id}" format (our code uses this)
    # - integer id format (what the dataset has)
    # - string id format (just in case)
    ground_truth_map = {}
    for dp in datapoints:
        dp_id = dp["id"]
        ground_truth = dp.get("ground_truth", {})

        # Add all possible key formats
        ground_truth_map[f"issue-{dp_id}"] = ground_truth  # "issue-1", "issue-2", etc.
        ground_truth_map[dp_id] = ground_truth  # 1, 2, 3, etc.
        ground_truth_map[str(dp_id)] = ground_truth  # "1", "2", "3", etc.

    return enrich_experiment_with_feedback(run_id, ground_truth_map, api_key, project)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m utils.enrich_events_with_feedback <run_id_or_name> [dataset_name]")
        print("")
        print("Arguments:")
        print("  run_id_or_name     HoneyHive evaluation run ID (UUID) or experiment name")
        print("  dataset_name       Dataset name to load ground truth from (default: 'mock')")
        print("")
        print("Examples:")
        print("  # Using run ID (UUID):")
        print("  python -m utils.enrich_events_with_feedback a1b2c3d4-1234-5678-90ab-cdef12345678")
        print("")
        print("  # Using experiment name:")
        print("  python -m utils.enrich_events_with_feedback \"Customer Support Experiment - api-test-v1\"")
        print("")
        print("  # List all recent experiments:")
        print("  python -m utils.enrich_events_with_feedback --list")
        sys.exit(1)

    # Handle --list flag
    if sys.argv[1] == "--list":
        api_key = os.getenv("HONEYHIVE_API_KEY")
        project = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")

        if not api_key:
            print("Error: HONEYHIVE_API_KEY not set")
            sys.exit(1)

        print(f"Fetching evaluation runs for project: {project}")
        print("")

        runs = list_evaluation_runs(api_key, project)

        if not runs:
            print("No evaluation runs found")
            sys.exit(0)

        print(f"Found {len(runs)} evaluation runs:")
        print("")
        for i, run in enumerate(runs[:20], 1):  # Show only first 20
            print(f"{i}. {run.get('name', 'Unnamed')}")
            print(f"   Run ID: {run.get('run_id')}")
            print(f"   Status: {run.get('status')}")
            print(f"   Created: {run.get('created_at')}")
            print(f"   Events: {len(run.get('event_ids', []))}")
            print("")

        sys.exit(0)

    run_id_or_name = sys.argv[1]
    dataset_name = sys.argv[2] if len(sys.argv) > 2 else "mock"

    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")

    if not api_key:
        print("Error: HONEYHIVE_API_KEY not set")
        sys.exit(1)

    # Check if input is a UUID or a name
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    if re.match(uuid_pattern, run_id_or_name, re.IGNORECASE):
        # It's a UUID
        run_id = run_id_or_name
        print(f"Using run ID: {run_id}")
    else:
        # It's a name, try to find it
        print(f"Searching for experiment: {run_id_or_name}")
        run_id = find_run_by_name(run_id_or_name, api_key, project)

        if not run_id:
            print(f"\n✗ Could not find experiment with name: {run_id_or_name}")
            print("\nRun with --list to see all available experiments")
            sys.exit(1)

        print(f"✓ Found run ID: {run_id}")

    print(f"Using dataset: {dataset_name}")
    print("")

    result = enrich_experiment_from_dataset(run_id, dataset_name)

    if result["success"]:
        print(f"\n✓ Successfully enriched events!")
        print(f"Stats: {result['stats']}")
    else:
        print(f"\n✗ Failed to enrich events: {result.get('error')}")
        if "traceback" in result:
            print(f"\nTraceback:\n{result['traceback']}")
        sys.exit(1)
