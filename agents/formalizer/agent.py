"""
agents/formalizer/agent.py
Converts research intent into formal software specifications.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from shared.base_agent import BaseAgent, OUTPUT_ROOT
from shared.llm_client import call_claude_json
from shared.message_schema import AgentName, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a software requirements engineer specializing in research-to-software translation.
Convert research intent into formal, traceable software specifications.
Respond ONLY with valid JSON. Never hallucinate requirements not in the source material.
"""


class FormalizerAgent(BaseAgent):
    name = AgentName.FORMALIZER

    def _execute(self) -> None:
        # Load paper analyst outputs
        intent = self._load_json("paper_analyst", "research_intent.json")
        concepts = self._load_json("paper_analyst", "domain_concepts.json")
        methods = self._load_json("paper_analyst", "methods_models.json")
        datasets = self._load_json("paper_analyst", "datasets.json")

        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "formalizing"})

        concept_model = self._build_concept_model(intent, concepts)
        requirements = self._derive_requirements(intent, methods, datasets)
        data_contracts = self._build_data_contracts(methods, datasets, concepts)
        ambiguity_log = self._build_ambiguity_log(concepts, requirements)

        self._write("concept_model.json", concept_model)
        self._write("functional_requirements.json", requirements)
        self._write("data_contracts.json", data_contracts)
        self._write("ambiguity_log.json", ambiguity_log)

        # Block on high-severity ambiguities
        high_severity = [a for a in ambiguity_log.get("items", []) if a.get("severity") == "high"]
        if high_severity:
            logger.warning("%d HIGH-severity ambiguities found — requesting human review.", len(high_severity))

        artifact_refs = [
            f"outputs/{self.run_id}/formalizer/functional_requirements.json",
            f"outputs/{self.run_id}/formalizer/data_contracts.json",
            f"outputs/{self.run_id}/formalizer/ambiguity_log.json",
        ]

        # HITL-2 checkpoint
        self._request_human_review("HITL-2", artifact_refs)

        self._post(
            to_agent=AgentName.ARCHITECT_DEVELOPER,
            message_type=MessageType.OUTPUT,
            payload={
                "requirements_path": artifact_refs[0],
                "data_contracts_path": artifact_refs[1],
                "concept_model_path": f"outputs/{self.run_id}/formalizer/concept_model.json",
            },
            artifact_refs=artifact_refs,
        )
        logger.info("Formalizer complete.")

    # ------------------------------------------------------------------
    # Formalization steps
    # ------------------------------------------------------------------

    def _build_concept_model(self, intent: dict, concepts: dict) -> dict:
        self._log_assumption(
            "All domain entities are derivable from domain_concepts + methods.",
            confidence=0.80, impact="medium",
        )
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Build an ontology / concept model from the following research intent and domain concepts.

Return JSON:
{{
  "entities": [{{"id": "E-001", "name": "...", "description": "...", "attributes": []}}],
  "relationships": [{{"from": "E-001", "to": "E-002", "type": "...", "cardinality": "1:N"}}]
}}

RESEARCH INTENT:
{json.dumps(intent, indent=2)[:6000]}

DOMAIN CONCEPTS:
{json.dumps(concepts, indent=2)[:4000]}""",
        )

    def _derive_requirements(self, intent: dict, methods: dict, datasets: dict) -> dict:
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Derive numbered functional requirements from the research intent.
Each requirement MUST trace to a research question ID (RQ-XXX).

Return JSON:
{{
  "items": [{{
    "id": "FR-001",
    "description": "...",
    "priority": "must|should|could",
    "rq_refs": ["RQ-001"],
    "acceptance_criteria": ["..."]
  }}]
}}

RESEARCH INTENT:
{json.dumps(intent, indent=2)[:6000]}

METHODS:
{json.dumps(methods, indent=2)[:4000]}

DATASETS:
{json.dumps(datasets, indent=2)[:2000]}""",
        )

    def _build_data_contracts(self, methods: dict, datasets: dict, concepts: dict) -> dict:
        self._log_assumption(
            "JSON Schema Draft-07 is sufficient to represent all data structures.",
            confidence=0.90, impact="low",
        )
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Generate JSON Schema Draft-07 data contracts for the key data structures 
described in the methods and datasets.

Return JSON:
{{
  "schemas": [{{
    "id": "schema_name",
    "description": "...",
    "json_schema": {{...valid JSON Schema Draft-07...}}
  }}]
}}

METHODS:
{json.dumps(methods, indent=2)[:5000]}

DATASETS:
{json.dumps(datasets, indent=2)[:3000]}

CONCEPTS:
{json.dumps(concepts, indent=2)[:2000]}""",
        )

    def _build_ambiguity_log(self, concepts: dict, requirements: dict) -> dict:
        ambiguous = [c for c in concepts.get("items", []) if c.get("ambiguous")]
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Review these ambiguous domain concepts and requirements. 
For each issue, assess severity and suggest resolution options.

Return JSON:
{{
  "items": [{{
    "id": "AMB-001",
    "source": "concept|requirement",
    "source_id": "DC-001",
    "description": "...",
    "severity": "low|medium|high",
    "resolution_options": ["option A", "option B"],
    "resolved": false,
    "resolution": null
  }}]
}}

AMBIGUOUS CONCEPTS:
{json.dumps(ambiguous, indent=2)}

REQUIREMENTS:
{json.dumps(requirements.get("items", [])[:10], indent=2)}""",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_json(self, agent_name: str, filename: str) -> dict:
        path = self._read_prior_output(agent_name, filename)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, filename: str, data: dict) -> None:
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Wrote %s", path)
