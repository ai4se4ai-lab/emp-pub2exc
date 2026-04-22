"""tests/agents/test_auditor_supervisor.py"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.auditor_supervisor.agent import AuditorSupervisorAgent

MOCK_TRACEABILITY = {
    "links": [
        {"requirement_id": "FR-001", "requirement_desc": "Implement X", "code_locations": [{"file": "src/x.py", "function": "run_x", "line": 10}], "fidelity": "exact", "notes": ""},
        {"requirement_id": "FR-002", "requirement_desc": "Implement Y", "code_locations": [], "fidelity": "missing", "notes": ""},
    ]
}
MOCK_REVIEW_POINTS = {"items": [{"id": "HRP-001", "type": "gap", "description": "FR-002 not implemented", "priority": "critical", "context": ""}]}
MOCK_DEVIATION_REPORT = {"deviations": [], "total_deviations": 0}
MOCK_REPORT_MD = "# Traceability Report\n\nAll findings..."


def make_prior_outputs(tmp_path):
    """Seed all prior agent outputs."""
    for agent, files in {
        "paper_analyst": {
            "research_intent.json": {"run_id": "r", "paper_path": "test.pdf"},
            "research_questions.json": {"items": []},
            "methods_models.json": {"items": []},
            "metrics_results.json": {"items": []},
        },
        "formalizer": {
            "functional_requirements.json": {"items": [{"id": "FR-001", "priority": "must"}, {"id": "FR-002", "priority": "must"}]},
            "data_contracts.json": {"schemas": []},
            "ambiguity_log.json": {"items": []},
        },
        "architect_developer": {
            "architecture.md": "# Architecture",
            "modules.json": {"modules": []},
        },
    }.items():
        d = tmp_path / "outputs" / "test-run" / agent
        d.mkdir(parents=True)
        for fname, content in files.items():
            p = d / fname
            if isinstance(content, str):
                p.write_text(content)
            else:
                p.write_text(json.dumps(content))


@pytest.fixture
def agent(tmp_path, monkeypatch):
    import shared.base_agent as ba
    monkeypatch.setattr(ba, "OUTPUT_ROOT", tmp_path / "outputs")
    monkeypatch.setattr(ba, "HUMAN_REVIEW_ENABLED", False)
    make_prior_outputs(tmp_path)
    return AuditorSupervisorAgent(run_id="test-run"), tmp_path


@patch("agents.auditor_supervisor.agent.call_claude")
@patch("agents.auditor_supervisor.agent.call_claude_json")
def test_auditor_writes_all_outputs(mock_json, mock_text, agent):
    ag, tmp_path = agent
    mock_json.side_effect = [MOCK_TRACEABILITY, MOCK_REVIEW_POINTS, MOCK_DEVIATION_REPORT]
    mock_text.return_value = MOCK_REPORT_MD

    ag.run()

    out_dir = tmp_path / "outputs" / "test-run" / "auditor_supervisor"
    assert (out_dir / "traceability_links.json").exists()
    assert (out_dir / "gaps.json").exists()
    assert (out_dir / "human_review_points.json").exists()
    assert (out_dir / "assumption_deviation_report.json").exists()
    assert (out_dir / "traceability_report.md").exists()


@patch("agents.auditor_supervisor.agent.call_claude")
@patch("agents.auditor_supervisor.agent.call_claude_json")
def test_gaps_detects_missing_requirements(mock_json, mock_text, agent):
    ag, tmp_path = agent
    mock_json.side_effect = [MOCK_TRACEABILITY, MOCK_REVIEW_POINTS, MOCK_DEVIATION_REPORT]
    mock_text.return_value = MOCK_REPORT_MD

    ag.run()

    gaps = json.loads((tmp_path / "outputs" / "test-run" / "auditor_supervisor" / "gaps.json").read_text())
    assert gaps["total_missing"] == 1
    assert gaps["items"][0]["requirement_id"] == "FR-002"
    assert gaps["items"][0]["severity"] == "critical"
