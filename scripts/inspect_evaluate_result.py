"""
Quick script to inspect what evaluate() returns and extract the run_id.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from honeyhive import evaluate, evaluator
from agents.support_agent import CustomerSupportAgent
from data.datasets import load_dataset


@evaluator()
def dummy_evaluator(outputs, inputs, ground_truths):
    """Simple evaluator for testing."""
    return 1


def test_evaluate_return():
    """Run a minimal experiment and inspect the return value."""

    # Create agent
    agent = CustomerSupportAgent(
        version="inspect-result",
        prompt_version="inspect-result",
        use_llm=True,
        provider="anthropic",
    )

    # Load just one datapoint
    datapoints = load_dataset("mock")
    test_case = datapoints[0]

    # Create inline dataset
    dataset = [{
        "inputs": {
            "id": test_case["id"],
            "customer": test_case.get("customer"),
            "issue": test_case["issue"],
        },
        "ground_truths": test_case.get("ground_truth", {}),
    }]

    # Function to evaluate
    def function_to_evaluate(inputs, ground_truths):
        ticket = {
            "id": inputs["id"],
            "customer": inputs.get("customer"),
            "issue": inputs["issue"],
        }
        result = agent.process_ticket(
            ticket,
            run_id="inspect-result",
            datapoint_id=inputs["id"],
            ground_truth=ground_truths,
        )
        answer = result.get("output", {}).get("answer", "")
        output_dict = result.get("output", {})
        return {
            "category": output_dict.get("category"),
            "response": answer,
        }

    # Run evaluation
    api_key = os.getenv("HONEYHIVE_API_KEY")
    project = os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo")

    result = evaluate(
        function=function_to_evaluate,
        api_key=api_key,
        project=project,
        name="Inspect Return Value Test",
        dataset=dataset,
        evaluators=[dummy_evaluator],
    )

    print("\n" + "=" * 60)
    print("EVALUATE() RETURN VALUE")
    print("=" * 60)
    print(f"Type: {type(result)}")
    print(f"\nFull result:")
    print(result)

    if isinstance(result, dict):
        print(f"\nKeys: {list(result.keys())}")
        for key, value in result.items():
            print(f"\n{key}: {value}")
            print(f"  Type: {type(value)}")

    # Try to extract run_id
    if isinstance(result, dict) and "run_id" in result:
        print(f"\n✓ Found run_id: {result['run_id']}")
    else:
        print("\n✗ No 'run_id' key found in result")
        print("Available keys:", list(result.keys()) if isinstance(result, dict) else "N/A")

    print("=" * 60)

    return result


if __name__ == "__main__":
    test_evaluate_return()
