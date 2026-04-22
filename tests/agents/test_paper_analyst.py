"""tests/agents/test_paper_analyst.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.paper_analyst.agent import PaperAnalystAgent


MOCK_RQS = {"items": [{"id": "RQ-001", "question": "How does X affect Y?", "type": "research_question", "confidence": 0.9}]}
MOCK_CONCEPTS = {"items": [{"id": "DC-001", "term": "X", "definition": "...", "ambiguous": False, "confidence": 0.85}]}
MOCK_METHODS = {"items": [{"id": "MM-001", "name": "Method A", "description": "...", "confidence": 0.8}]}
MOCK_DATASETS = {"items": [{"id": "DS-001", "name": "Dataset A", "description": "...", "confidence": 0.9}]}
MOCK_METRICS = {"items": [{"id": "MR-001", "metric": "Accuracy", "value": 0.95, "confidence": 0.9}]}


@pytest.fixture
def paper_file(tmp_path):
    p = tmp_path / "paper.txt"
    p.write_text("Title: Test Paper\nAbstract: We study X and Y.\nMethod: We use approach Z.")
    return p


@pytest.fixture
def agent(tmp_path, paper_file, monkeypatch):
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "outputs"))
    monkeypatch.setenv("HUMAN_REVIEW_ENABLED", "false")
    import shared.base_agent as ba
    monkeypatch.setattr(ba, "OUTPUT_ROOT", tmp_path / "outputs")
    monkeypatch.setattr(ba, "HUMAN_REVIEW_ENABLED", False)
    return PaperAnalystAgent(run_id="test-run-001", paper_path=paper_file)


@patch("agents.paper_analyst.agent.call_claude_json")
def test_full_execution_writes_all_files(mock_llm, agent, tmp_path):
    mock_llm.side_effect = [MOCK_RQS, MOCK_CONCEPTS, MOCK_METHODS, MOCK_DATASETS, MOCK_METRICS]

    agent.run()

    out_dir = tmp_path / "outputs" / "test-run-001" / "paper_analyst"
    assert (out_dir / "research_intent.json").exists()
    assert (out_dir / "research_questions.json").exists()
    assert (out_dir / "domain_concepts.json").exists()
    assert (out_dir / "methods_models.json").exists()
    assert (out_dir / "datasets.json").exists()
    assert (out_dir / "metrics_results.json").exists()


@patch("agents.paper_analyst.agent.call_claude_json")
def test_research_intent_contains_all_sections(mock_llm, agent, tmp_path):
    mock_llm.side_effect = [MOCK_RQS, MOCK_CONCEPTS, MOCK_METHODS, MOCK_DATASETS, MOCK_METRICS]
    agent.run()

    intent = json.loads(
        (tmp_path / "outputs" / "test-run-001" / "paper_analyst" / "research_intent.json").read_text()
    )
    assert "research_questions" in intent
    assert "domain_concepts" in intent
    assert "methods_models" in intent
    assert "datasets" in intent
    assert "metrics_results" in intent


@patch("agents.paper_analyst.agent.call_claude_json")
def test_posts_output_message_to_formalizer(mock_llm, agent, tmp_path, monkeypatch):
    mock_llm.side_effect = [MOCK_RQS, MOCK_CONCEPTS, MOCK_METHODS, MOCK_DATASETS, MOCK_METRICS]

    posted = []

    import shared.channel as ch
    monkeypatch.setattr(ch, "CHANNEL_DIR", tmp_path / ".comms")
    monkeypatch.setattr(ch, "CHANNEL_FILE", tmp_path / ".comms" / "channel.jsonl")

    agent.run()

    from shared.channel import read_messages
    from shared.message_schema import AgentName, MessageType
    msgs = read_messages(run_id="test-run-001", to_agent=AgentName.FORMALIZER)
    assert any(m.message_type == MessageType.OUTPUT for m in msgs)
