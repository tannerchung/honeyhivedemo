import pytest

from agents.support_agent import CustomerSupportAgent


def test_process_ticket_produces_steps():
    agent = CustomerSupportAgent(api_key=None, use_llm=False)
    ticket = {"id": "test", "customer": "Test", "issue": "Upload gives 404"}
    result = agent.process_ticket(ticket)

    assert result["ticket_id"] == "test"
    assert "steps" in result
    assert set(result["steps"].keys()) == {"route", "retrieve", "generate"}
    assert "answer" in result["steps"]["generate"]
    assert result["output"]["category"] in {"upload_errors", "account_access", "data_export", "other"}


def test_generate_response_has_action_steps():
    agent = CustomerSupportAgent(api_key=None, use_llm=False)
    docs = ["Doc one", "Doc two"]
    output = agent.generate_response("Issue", docs, category="upload_errors")
    assert output["has_action_steps"] is True
    assert isinstance(output.get("steps"), list)
