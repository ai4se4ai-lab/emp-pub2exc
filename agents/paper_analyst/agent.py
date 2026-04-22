"""
agents/paper_analyst/agent.py
Extracts structured research intent from an academic paper.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from shared.base_agent import BaseAgent
from shared.llm_client import call_claude_json
from shared.message_schema import AgentName, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a research analysis specialist. Extract structured information from academic papers 
with high fidelity. Preserve exact terminology. Assign confidence scores (0.0–1.0) to each 
extracted item. Flag ambiguous items rather than guessing. Respond ONLY with valid JSON.
"""


class PaperAnalystAgent(BaseAgent):
    name = AgentName.PAPER_ANALYST

    def __init__(self, run_id: str, paper_path: Path) -> None:
        super().__init__(run_id)
        self.paper_path = paper_path

    def _execute(self) -> None:
        paper_text = self._load_paper()
        self._post(AgentName.BROADCAST, MessageType.STATUS, {"status": "parsing_paper"})

        research_questions = self._extract_research_questions(paper_text)
        domain_concepts = self._extract_domain_concepts(paper_text)
        methods_models = self._extract_methods(paper_text)
        datasets = self._extract_datasets(paper_text)
        metrics_results = self._extract_metrics(paper_text)

        # Write individual output files
        self._write("research_questions.json", research_questions)
        self._write("domain_concepts.json", domain_concepts)
        self._write("methods_models.json", methods_models)
        self._write("datasets.json", datasets)
        self._write("metrics_results.json", metrics_results)

        # Assemble top-level research intent
        intent = {
            "run_id": self.run_id,
            "paper_path": str(self.paper_path),
            "research_questions": research_questions.get("items", []),
            "domain_concepts": domain_concepts.get("items", []),
            "methods_models": methods_models.get("items", []),
            "datasets": datasets.get("items", []),
            "metrics_results": metrics_results.get("items", []),
        }
        self._write("research_intent.json", intent)

        artifact_refs = [
            f"outputs/{self.run_id}/paper_analyst/research_intent.json",
            f"outputs/{self.run_id}/paper_analyst/domain_concepts.json",
        ]

        # HITL-1 checkpoint
        self._request_human_review("HITL-1", artifact_refs)

        self._post(
            to_agent=AgentName.FORMALIZER,
            message_type=MessageType.OUTPUT,
            payload={"research_intent_path": artifact_refs[0]},
            artifact_refs=artifact_refs,
        )
        logger.info("Paper Analyst complete. Research intent written.")

    # ------------------------------------------------------------------
    # Paper loading
    # ------------------------------------------------------------------

    def _load_paper(self) -> str:
        suffix = self.paper_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text()
        return self.paper_path.read_text(encoding="utf-8")

    def _extract_pdf_text(self) -> str:
        try:
            import pdfminer.high_level as pdfminer
            return pdfminer.extract_text(str(self.paper_path))
        except ImportError:
            logger.warning("pdfminer not installed — reading PDF as binary text (may be garbled)")
            return self.paper_path.read_bytes().decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Extraction steps (each isolated Claude call)
    # ------------------------------------------------------------------

    def _extract_research_questions(self, text: str) -> dict:
        self._log_assumption(
            "Research questions are explicitly stated or clearly implied in abstract/intro.",
            confidence=0.85, impact="high",
        )
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Extract all research questions and hypotheses from this paper.

Return JSON: {{"items": [{{"id": "RQ-001", "question": "...", "type": "research_question|hypothesis", "section": "...", "confidence": 0.0}}]}}

PAPER:
{text[:12000]}""",
        )

    def _extract_domain_concepts(self, text: str) -> dict:
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Extract all key domain concepts, terms, and assumptions from this paper.

Return JSON: {{"items": [{{"id": "DC-001", "term": "...", "definition": "...", "ambiguous": false, "confidence": 0.0}}]}}

PAPER:
{text[:12000]}""",
        )

    def _extract_methods(self, text: str) -> dict:
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Extract all methods, models, and algorithms described in this paper.

Return JSON: {{"items": [{{"id": "MM-001", "name": "...", "description": "...", "parameters": {{}}, "implementation_hints": [], "rq_refs": ["RQ-001"], "confidence": 0.0}}]}}

PAPER:
{text[:16000]}""",
        )

    def _extract_datasets(self, text: str) -> dict:
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Extract all datasets, data splits, and experimental settings described.

Return JSON: {{"items": [{{"id": "DS-001", "name": "...", "description": "...", "splits": {{}}, "preprocessing": [], "source_url": "", "confidence": 0.0}}]}}

PAPER:
{text[:12000]}""",
        )

    def _extract_metrics(self, text: str) -> dict:
        return call_claude_json(
            system=SYSTEM_PROMPT,
            user=f"""Extract all evaluation metrics and reported results from this paper.

Return JSON: {{"items": [{{"id": "MR-001", "metric": "...", "value": null, "condition": "...", "rq_refs": [], "confidence": 0.0}}]}}

PAPER:
{text[:12000]}""",
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _write(self, filename: str, data: dict) -> None:
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Wrote %s", path)
