import pytest

from agents.support_agent import CustomerSupportAgent


def test_process_ticket_produces_steps():
    agent = CustomerSupportAgent(api_key=None)
    ticket = {"id": "test", "customer": "Test", "issue": "Upload gives 404"}
    result = agent.process_ticket(ticket)

    assert result["ticket_id"] == "test"
    assert "steps" in result
    assert set(result["steps"].keys()) == {"step_1", "step_2", "step_3"}
    assert "response" in result["steps"]["step_3"]
    assert result["output"]["category"] in {"upload_errors", "account_access", "data_export", "other"}


def test_generate_response_has_action_steps():
    agent = CustomerSupportAgent(api_key=None)
    docs = ["Doc one", "Doc two"]
    output = agent.generate_response("Issue", docs)
    assert output["has_action_steps"] is True
