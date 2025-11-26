"""
Script to inspect the event object structure in HoneyHive evaluators.
This will help us understand what's available in event["feedback"].
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from honeyhive import evaluator, evaluate
except ImportError:
    print("HoneyHive SDK not available")
    exit(1)

from agents.support_agent import CustomerSupportAgent
from data.datasets import load_dataset


@evaluator()
def inspect_event_structure(outputs, inputs, ground_truths):
    """
    Inspect the event object to see what's available.
    Note: In the UI evaluator context, we have access to the 'event' object.
    But in the SDK @evaluator decorator, we only get outputs, inputs, ground_truths.
    """
    print("\n=== EVALUATOR FUNCTION INPUTS ===")
    print(f"Type of outputs: {type(outputs)}")
    print(f"outputs keys: {outputs.keys() if isinstance(outputs, dict) else 'N/A'}")
    print(f"outputs: {outputs}")
    print()
    print(f"Type of inputs: {type(inputs)}")
    print(f"inputs keys: {inputs.keys() if isinstance(inputs, dict) else 'N/A'}")
    print(f"inputs: {inputs}")
    print()
    print(f"Type of ground_truths: {type(ground_truths)}")
    print(f"ground_truths keys: {ground_truths.keys() if isinstance(ground_truths, dict) else 'N/A'}")
    print(f"ground_truths: {ground_truths}")
    print("\n=== END EVALUATOR INPUTS ===\n")
    return 1


def test_event_structure():
    """Run a single test case to inspect the event structure."""

    # Create agent
    agent = CustomerSupportAgent(
        version="event-inspect",
        prompt_version="event-inspect",
        use_llm=True,
        provider="anthropic",
    )

    # Load one datapoint
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
        """Process a single ticket through the agent."""
        try:
            from honeyhive import enrich_session
        except ImportError:
            enrich_session = None

        # Enrich the session with ground truth
        if enrich_session and ground_truths:
            print(f"\n=== ENRICHING SESSION ===")
            print(f"ground_truths being enriched: {ground_truths}")
            print(f"Structure: {{'ground_truth': ground_truths}}")
            enrich_session(feedback={"ground_truth": ground_truths})
            print(f"=== SESSION ENRICHED ===\n")

        ticket = {
            "id": inputs["id"],
            "customer": inputs.get("customer"),
            "issue": inputs["issue"],
        }
        result = agent.process_ticket(
            ticket,
            run_id="event-inspect",
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
    project = os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")

    result = evaluate(
        function=function_to_evaluate,
        api_key=api_key,
        project=project,
        name="Event Structure Inspection",
        dataset=dataset,
        evaluators=[inspect_event_structure],
    )

    print(f"\n=== EVALUATION COMPLETE ===")
    print(f"Result: {result}")


if __name__ == "__main__":
    test_event_structure()
