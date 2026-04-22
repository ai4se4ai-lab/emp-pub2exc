"""tests/shared/test_message_schema.py"""
import pytest
from shared.message_schema import AgentMessage, AgentName, MessageType, Assumption


def test_agent_message_defaults():
    msg = AgentMessage(
        run_id="test-run",
        from_agent=AgentName.PAPER_ANALYST,
        to_agent=AgentName.FORMALIZER,
        message_type=MessageType.OUTPUT,
    )
    assert msg.run_id == "test-run"
    assert msg.message_id is not None
    assert msg.timestamp is not None
    assert msg.payload == {}
    assert msg.artifact_refs == []


def test_agent_message_serialization():
    msg = AgentMessage(
        run_id="test-run",
        from_agent=AgentName.FORMALIZER,
        to_agent=AgentName.BROADCAST,
        message_type=MessageType.STATUS,
        payload={"status": "running"},
    )
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.run_id == msg.run_id
    assert restored.payload["status"] == "running"


def test_assumption_fields():
    a = Assumption(
        agent=AgentName.PAPER_ANALYST,
        run_id="test-run",
        assumption="Test assumption",
        confidence=0.85,
        impact="medium",
    )
    assert 0.0 <= a.confidence <= 1.0
    assert a.impact == "medium"


def test_assumption_confidence_bounds():
    with pytest.raises(Exception):
        Assumption(
            agent=AgentName.FORMALIZER,
            run_id="r",
            assumption="bad",
            confidence=1.5,  # out of bounds
            impact="low",
        )
