"""
Verify that token usage is being captured in experiment events.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HONEYHIVE_API_KEY")
PROJECT = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")


def get_run_events(run_id: str):
    """Fetch all events for a run."""
    url = f"https://api.honeyhive.ai/runs/{run_id}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers)
    data = response.json()
    evaluation = data.get("evaluation", {})
    event_ids = evaluation.get("event_ids", [])
    return event_ids


def get_event_with_children(event_id: str):
    """Fetch an event with its children."""
    url = f"https://api.honeyhive.ai/events/{event_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"project": PROJECT}
    response = requests.get(url, headers=headers, params=params)
    return response.json()


def extract_llm_token_usage(event):
    """Recursively extract token usage from LLM completion events."""
    tokens = []

    # Check if this is an LLM event
    event_type = event.get("event_type")
    event_name = event.get("event_name")
    metadata = event.get("metadata", {})

    if event_type == "model" and ("anthropic.chat" in event_name or "openai.chat" in event_name):
        token_data = {
            "event_id": event.get("event_id"),
            "event_name": event_name,
            "prompt_tokens": metadata.get("prompt_tokens", 0),
            "completion_tokens": metadata.get("completion_tokens", 0),
            "total_tokens": metadata.get("total_tokens", 0),
            "model": metadata.get("model_name", "unknown"),
        }
        tokens.append(token_data)

    # Recursively check children
    for child in event.get("children", []):
        tokens.extend(extract_llm_token_usage(child))

    return tokens


def analyze_run_token_usage(run_id: str, run_name: str):
    """Analyze token usage for a run."""
    print(f"\nAnalyzing: {run_name}")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    event_ids = get_run_events(run_id)
    print(f"Total events: {len(event_ids)}")

    all_tokens = []
    for event_id in event_ids:
        event = get_event_with_children(event_id)
        llm_tokens = extract_llm_token_usage(event)
        all_tokens.extend(llm_tokens)

    if all_tokens:
        total_prompt = sum(t["prompt_tokens"] for t in all_tokens)
        total_completion = sum(t["completion_tokens"] for t in all_tokens)
        total = sum(t["total_tokens"] for t in all_tokens)

        print(f"\nLLM API Calls: {len(all_tokens)}")
        print(f"Total Prompt Tokens: {total_prompt:,}")
        print(f"Total Completion Tokens: {total_completion:,}")
        print(f"Total Tokens: {total:,}")

        print(f"\nPer-call breakdown:")
        for i, token_data in enumerate(all_tokens, 1):
            print(f"  {i}. {token_data['event_name']} ({token_data['model']})")
            print(f"     Prompt: {token_data['prompt_tokens']}, Completion: {token_data['completion_tokens']}, Total: {token_data['total_tokens']}")
    else:
        print("\n⚠️  No LLM token usage found!")

    return all_tokens


if __name__ == "__main__":
    # Analyze both experiments
    claude_run = "bf6f39a6-04c3-4a1d-9a9b-1b0dce63ebb2"
    openai_run = "c97c8917-7c37-4217-bb30-0f6f76c62d76"

    claude_tokens = analyze_run_token_usage(claude_run, "Claude Sonnet (LLM Model)")
    openai_tokens = analyze_run_token_usage(openai_run, "GPT-4o (LLM Model)")

    # Summary comparison
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    if claude_tokens and openai_tokens:
        claude_total = sum(t["total_tokens"] for t in claude_tokens)
        openai_total = sum(t["total_tokens"] for t in openai_tokens)

        print(f"Claude Total Tokens: {claude_total:,}")
        print(f"OpenAI Total Tokens: {openai_total:,}")
        print(f"Difference: {abs(claude_total - openai_total):,} tokens")
        print(f"Winner (fewer tokens): {'Claude' if claude_total < openai_total else 'OpenAI'}")
    else:
        print("⚠️  Could not compare - missing token data")
