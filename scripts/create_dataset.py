"""
Script to create and optionally upload HoneyHive dataset.

This generates a properly formatted dataset from your mock tickets and ground truth,
and can optionally upload it to HoneyHive for centralized management.
"""

import json
import os
from typing import List, Dict, Any

# Add parent directory to path to import data modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import MOCK_TICKETS, GROUND_TRUTH


def create_honeyhive_dataset() -> List[Dict[str, Any]]:
    """
    Convert mock tickets and ground truth into HoneyHive dataset format.

    Format:
    [
      {
        "inputs": {
          "id": "1",
          "customer": "Alice",
          "issue": "I'm getting a 404 error..."
        },
        "ground_truths": {
          "expected_category": "upload_errors",
          "expected_keywords": ["404", "path"],
          "has_action_steps": true
        }
      },
      ...
    ]
    """
    dataset = []

    for ticket in MOCK_TICKETS:
        ticket_id = ticket["id"]
        ground_truth = GROUND_TRUTH.get(ticket_id, {})

        datapoint = {
            "inputs": {
                "id": ticket["id"],
                "customer": ticket["customer"],
                "issue": ticket["issue"],
            },
            "ground_truths": {
                "expected_category": ground_truth.get("expected_category"),
                "expected_keywords": ground_truth.get("expected_keywords", []),
                "expected_tone": ground_truth.get("expected_tone"),
                "has_action_steps": ground_truth.get("has_action_steps", True),
            }
        }

        dataset.append(datapoint)

    return dataset


def save_dataset_to_file(dataset: List[Dict[str, Any]], filename: str = "honeyhive_dataset.json"):
    """Save dataset to JSON file for manual upload or reference."""
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        filename
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"✓ Dataset saved to: {output_path}")
    print(f"  {len(dataset)} datapoints")
    return output_path


def upload_to_honeyhive(dataset: List[Dict[str, Any]], dataset_name: str = "customer_support_demo"):
    """
    Upload dataset to HoneyHive using the SDK.

    Note: As of HoneyHive SDK 0.2.57, dataset management might use different APIs.
    This function attempts to use the available SDK methods.
    """
    try:
        from honeyhive import HoneyHive
    except ImportError:
        print("✗ HoneyHive SDK not available")
        return {"success": False, "reason": "SDK not installed"}

    api_key = os.getenv("HONEYHIVE_API_KEY")
    if not api_key:
        print("✗ HONEYHIVE_API_KEY not found in environment")
        return {"success": False, "reason": "Missing API key"}

    try:
        client = HoneyHive(bearer_auth=api_key)

        # Check if SDK has datasets endpoint
        if hasattr(client, 'datasets'):
            print(f"Uploading dataset '{dataset_name}' to HoneyHive...")

            # Try to create or update dataset
            # Note: The exact API might differ - this is a best-effort attempt
            try:
                response = client.datasets.create(
                    name=dataset_name,
                    data=dataset,
                )
                print(f"✓ Dataset uploaded successfully")
                return {"success": True, "response": response}
            except Exception as e:
                print(f"✗ Upload failed: {str(e)}")
                print("\nNote: You may need to upload manually via the HoneyHive UI")
                print("      or use the HoneyHive CLI if available.")
                return {"success": False, "reason": str(e)}
        else:
            print("✗ Dataset upload not available in this SDK version")
            print("   Use the generated JSON file for manual upload")
            return {"success": False, "reason": "SDK version doesn't support dataset upload"}

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return {"success": False, "reason": str(e)}


def main():
    """Create dataset and optionally upload to HoneyHive."""
    import argparse

    parser = argparse.ArgumentParser(description="Create HoneyHive dataset from mock data")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Attempt to upload dataset to HoneyHive (requires API key)"
    )
    parser.add_argument(
        "--name",
        default="customer_support_demo",
        help="Dataset name in HoneyHive (default: customer_support_demo)"
    )
    parser.add_argument(
        "--output",
        default="honeyhive_dataset.json",
        help="Output filename (default: honeyhive_dataset.json)"
    )

    args = parser.parse_args()

    print("Creating HoneyHive dataset from mock data...\n")

    # Create dataset
    dataset = create_honeyhive_dataset()

    # Save to file
    filepath = save_dataset_to_file(dataset, args.output)

    # Show preview
    print(f"\nDataset preview (first entry):")
    print(json.dumps(dataset[0], indent=2))

    # Optionally upload
    if args.upload:
        print(f"\nAttempting to upload to HoneyHive...")
        result = upload_to_honeyhive(dataset, args.name)

        if not result.get("success"):
            print(f"\n📋 Manual Upload Instructions:")
            print(f"   1. Open app.honeyhive.ai")
            print(f"   2. Navigate to Datasets")
            print(f"   3. Create new dataset named '{args.name}'")
            print(f"   4. Upload the file: {filepath}")
    else:
        print(f"\n💡 To upload to HoneyHive, run with --upload flag")
        print(f"   Or manually upload {filepath} via the HoneyHive UI")

    print(f"\n✓ Done! Dataset ready for evaluation.")


if __name__ == "__main__":
    main()
