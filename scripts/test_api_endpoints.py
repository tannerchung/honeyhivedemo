"""
Test script to explore HoneyHive API endpoints for updating event feedback.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HONEYHIVE_API_KEY")
PROJECT = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")
BASE_URL = "https://api.honeyhive.ai"

def test_update_event_feedback(event_id: str):
    """Test updating event feedback via PUT."""
    url = f"{BASE_URL}/events"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "event_id": event_id,
        "feedback": {
            "ground_truth": {
                "expected_category": "billing",
                "expected_keywords": ["invoice", "payment"],
            }
        }
    }

    print(f"Testing PUT {url}")
    print(f"Payload: {payload}")
    response = requests.put(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response

def test_get_session(session_id: str):
    """Test retrieving a session."""
    url = f"{BASE_URL}/session/{session_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }

    print(f"\nTesting GET {url}")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Session found!")
        print(f"Session keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
        if isinstance(data, dict) and 'events' in data:
            print(f"Number of events: {len(data['events'])}")
    else:
        print(f"Response: {response.text}")
    return response

def test_update_session_feedback(session_id: str):
    """Test updating session feedback via PATCH."""
    url = f"{BASE_URL}/session/{session_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "project": PROJECT,
        "feedback": {
            "ground_truth": {
                "expected_category": "billing",
            }
        }
    }

    print(f"\nTesting PATCH {url}")
    response = requests.patch(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python test_api_endpoints.py <session_id> <event_id>")
        print("\nExample:")
        print("  python test_api_endpoints.py abc123 def456")
        sys.exit(1)

    session_id = sys.argv[1]
    event_id = sys.argv[2]

    print("=" * 60)
    print("Testing HoneyHive API Endpoints")
    print("=" * 60)

    # Test 1: Get session
    test_get_session(session_id)

    # Test 2: Update session feedback
    test_update_session_feedback(session_id)

    # Test 3: Update event feedback
    test_update_event_feedback(event_id)

    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
