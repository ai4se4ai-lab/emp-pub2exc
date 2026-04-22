"""tests/agents/test_formalizer.py"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.formalizer.agent import FormalizerAgent

MOCK_INTENT = {
    "run_id": "test-run",
    "research_questions": [{"id": "RQ-001", "question": "How does X affect Y?"}],
}
MOCK_CONCEPTS = {"items": [{"id": "DC-001", "term": "X", "ambiguous": False}]}
MOCK_METHODS = {"items": [{"id": "MM-001", "name": "Method A"}]}
MOCK_DATASETS = {"items": [{"id": "DS-001", "name": "Dataset A"}]}

MOCK_CONCEPT_MODEL = {"entities": [{"id": "E-001", "name": "X"}], "relationships": []}
MOCK_REQUIREMENTS = {"items": [{"id": "FR-001", "description": "Implement X", "priority": "must", "rq_refs": ["RQ-001"], "acceptance_criteria": []}]}
MOCK_DATA_CONTRACTS = {"schemas": [{"id": "XSchema", "description": "...", "json_schema": {"type": "object"}}]}
MOCK_AMBIGUITY_LOG = {"items": []}


@pytest.fixture
def agent_with_prior_outputs(tmp_path, monkeypatch):
    import shared.base_agent as ba
    monkeypatch.setattr(ba, "OUTPUT_ROOT", tmp_path / "outputs")
    monkeypatch.setattr(ba, "HUMAN_REVIEW_ENABLED", False)

    # Create paper_analyst outputs
    pa_dir = tmp_path / "outputs" / "test-run" / "paper_analyst"
    pa_dir.mkdir(parents=True)
    (pa_dir / "research_intent.json").write_text(json.dumps(MOCK_INTENT))
    (pa_dir / "domain_concepts.json").write_text(json.dumps(MOCK_CONCEPTS))
    (pa_dir / "methods_models.json").write_text(json.dumps(MOCK_METHODS))
    (pa_dir / "datasets.json").write_text(json.dumps(MOCK_DATASETS))

    return FormalizerAgent(run_id="test-run")


@patch("agents.formalizer.agent.call_claude_json")
def test_formalizer_writes_all_outputs(mock_llm, agent_with_prior_outputs, tmp_path):
    mock_llm.side_effect = [MOCK_CONCEPT_MODEL, MOCK_REQUIREMENTS, MOCK_DATA_CONTRACTS, MOCK_AMBIGUITY_LOG]
    agent_with_prior_outputs.run()

    out_dir = tmp_path / "outputs" / "test-run" / "formalizer"
    assert (out_dir / "concept_model.json").exists()
    assert (out_dir / "functional_requirements.json").exists()
    assert (out_dir / "data_contracts.json").exists()
    assert (out_dir / "ambiguity_log.json").exists()


@patch("agents.formalizer.agent.call_claude_json")
def test_requirements_have_ids(mock_llm, agent_with_prior_outputs, tmp_path):
    mock_llm.side_effect = [MOCK_CONCEPT_MODEL, MOCK_REQUIREMENTS, MOCK_DATA_CONTRACTS, MOCK_AMBIGUITY_LOG]
    agent_with_prior_outputs.run()

    reqs = json.loads((tmp_path / "outputs" / "test-run" / "formalizer" / "functional_requirements.json").read_text())
    for item in reqs.get("items", []):
        assert "id" in item
        assert item["id"].startswith("FR-")


@patch("agents.formalizer.agent.call_claude_json")
def test_missing_prior_output_raises(mock_llm, tmp_path, monkeypatch):
    import shared.base_agent as ba
    monkeypatch.setattr(ba, "OUTPUT_ROOT", tmp_path / "outputs")
    monkeypatch.setattr(ba, "HUMAN_REVIEW_ENABLED", False)
    # No paper_analyst outputs created — should raise FileNotFoundError
    agent = FormalizerAgent(run_id="no-prior-run")
    with pytest.raises(FileNotFoundError):
        agent.run()
