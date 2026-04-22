"""tests/shared/test_channel.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.message_schema import AgentMessage, AgentName, MessageType


@pytest.fixture(autouse=True)
def temp_comms(tmp_path, monkeypatch):
    """Redirect .comms to a temp dir for each test."""
    import shared.channel as ch
    monkeypatch.setattr(ch, "CHANNEL_DIR", tmp_path / ".comms")
    monkeypatch.setattr(ch, "CHANNEL_FILE", tmp_path / ".comms" / "channel.jsonl")
    yield


def make_msg(**kwargs) -> AgentMessage:
    defaults = dict(
        run_id="run-abc",
        from_agent=AgentName.PAPER_ANALYST,
        to_agent=AgentName.FORMALIZER,
        message_type=MessageType.OUTPUT,
    )
    defaults.update(kwargs)
    return AgentMessage(**defaults)


def test_post_and_read_message():
    from shared.channel import post_message, read_messages
    msg = make_msg()
    post_message(msg)
    results = read_messages(run_id="run-abc")
    assert len(results) == 1
    assert results[0].message_id == msg.message_id


def test_filter_by_message_type():
    from shared.channel import post_message, read_messages
    post_message(make_msg(message_type=MessageType.OUTPUT))
    post_message(make_msg(message_type=MessageType.ERROR))
    errors = read_messages(run_id="run-abc", message_type=MessageType.ERROR)
    assert len(errors) == 1
    assert errors[0].message_type == MessageType.ERROR


def test_filter_by_run_id():
    from shared.channel import post_message, read_messages
    post_message(make_msg(run_id="run-1"))
    post_message(make_msg(run_id="run-2"))
    results = read_messages(run_id="run-1")
    assert all(m.run_id == "run-1" for m in results)
    assert len(results) == 1


def test_broadcast_received_by_any_to_agent_filter():
    from shared.channel import post_message, read_messages
    post_message(make_msg(to_agent=AgentName.BROADCAST, message_type=MessageType.STATUS))
    # When filtering for formalizer, broadcast messages should still appear
    results = read_messages(run_id="run-abc", to_agent=AgentName.FORMALIZER)
    assert len(results) == 1


def test_empty_channel_returns_empty_list():
    from shared.channel import read_messages
    results = read_messages(run_id="nonexistent")
    assert results == []
