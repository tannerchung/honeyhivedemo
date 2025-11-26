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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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

    Uses the datasets.create_dataset() API to create a visible dataset in the UI.
    """
    try:
        from honeyhive import HoneyHive
        from honeyhive.models.components import CreateDatasetRequest
        from honeyhive.models.operations.adddatapoints import AddDatapointsRequestBody, Mapping
    except ImportError:
        print("✗ HoneyHive SDK not available")
        return {"success": False, "reason": "SDK not installed"}

    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")

    if not api_key:
        print("✗ HONEYHIVE_API_KEY not found in environment")
        return {"success": False, "reason": "Missing API key"}

    try:
        client = HoneyHive(bearer_auth=api_key)
        print(f"Creating dataset '{dataset_name}' in project '{project}'...")

        # Create the dataset first
        try:
            dataset_request = CreateDatasetRequest(
                name=dataset_name,
                project=project,
                description="Customer support demo dataset with 10 test cases covering upload errors, account access, and data export categories.",
                type="evaluation",  # or "fine_tuning" depending on use case
            )
            dataset_response = client.datasets.create_dataset(
                request=dataset_request
            )
            print(f"✓ Dataset '{dataset_name}' created successfully")

            # Extract dataset_id from response object
            dataset_id = None
            if hasattr(dataset_response, 'object') and hasattr(dataset_response.object, 'result'):
                dataset_id = dataset_response.object.result.inserted_id

            if dataset_id:
                print(f"  Dataset ID: {dataset_id}")

                # Add datapoints to the dataset
                print(f"Adding {len(dataset)} datapoints...")

                # Define mapping: which fields map to inputs/ground_truth/history
                mapping = Mapping(
                    inputs=["id", "customer", "issue"],
                    ground_truth=["expected_category", "expected_keywords", "expected_tone", "has_action_steps"],
                    history=[]  # No conversation history in this demo
                )

                # Flatten dataset for add_datapoints API
                # API expects flat list of dicts with all fields at top level
                flat_data = []
                for dp in dataset:
                    flat = {}
                    flat.update(dp.get("inputs", {}))
                    flat.update(dp.get("ground_truths", {}))
                    flat_data.append(flat)

                try:
                    request_body = AddDatapointsRequestBody(
                        project=project,
                        data=flat_data,
                        mapping=mapping
                    )
                    response = client.datasets.add_datapoints(
                        dataset_id=dataset_id,
                        request_body=request_body
                    )
                    print(f"  ✓ Added all {len(dataset)} datapoints")
                except Exception as e:
                    print(f"  ⚠ Failed to add datapoints: {str(e)}")

                print(f"✓ Dataset upload complete!")
                return {"success": True, "dataset_id": dataset_id}
            else:
                print("⚠ Dataset created but no ID returned")
                return {"success": True, "dataset_id": None}

        except Exception as e:
            error_msg = str(e)
            print(f"✗ Upload failed: {error_msg}")

            # Check if it's a "already exists" error
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print("\n💡 Dataset might already exist. Try:")
                print(f"   1. Delete the existing dataset '{dataset_name}' in HoneyHive UI")
                print(f"   2. Or use a different --name")
            else:
                print("\n📋 Manual Upload Instructions:")
                print(f"   1. Open app.honeyhive.ai")
                print(f"   2. Navigate to Datasets")
                print(f"   3. Create new dataset named '{dataset_name}'")
                print(f"   4. Upload the generated JSON file")

            return {"success": False, "reason": error_msg}

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
