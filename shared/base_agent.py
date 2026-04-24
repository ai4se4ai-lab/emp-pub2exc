"""
shared/base_agent.py
Abstract base class for all pipeline agents.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from shared.channel import post_message, log_assumption
from shared.llm_client import load_env_file
from shared.message_schema import (
    AgentMessage,
    AgentName,
    Assumption,
    MessageType,
)

logger = logging.getLogger(__name__)

load_env_file()
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "outputs"))
HUMAN_REVIEW_ENABLED = os.getenv("HUMAN_REVIEW_ENABLED", "true").lower() == "true"


class BaseAgent(ABC):
    name: AgentName

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.output_dir = OUTPUT_ROOT / run_id / self.name.value
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(f"agent.{self.name.value}")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute this agent's full pipeline stage."""
        self._logger.info("Starting agent: %s | run_id=%s", self.name.value, self.run_id)
        try:
            self._execute()
        except Exception as exc:
            self._logger.exception("Agent %s failed: %s", self.name.value, exc)
            self._post(
                to_agent=AgentName.BROADCAST,
                message_type=MessageType.ERROR,
                payload={"stage": self.name.value},
                error_detail=str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # To be implemented by each agent
    # ------------------------------------------------------------------

    @abstractmethod
    def _execute(self) -> None:
        """Agent-specific logic."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _post(
        self,
        to_agent: AgentName,
        message_type: MessageType,
        payload: dict | None = None,
        artifact_refs: list[str] | None = None,
        error_detail: str | None = None,
    ) -> None:
        msg = AgentMessage(
            run_id=self.run_id,
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload or {},
            artifact_refs=artifact_refs or [],
            error_detail=error_detail,
        )
        post_message(msg)
        self._logger.debug("Posted message: %s → %s [%s]", self.name.value, to_agent.value, message_type.value)

    def _log_assumption(self, assumption: str, confidence: float, impact: str, context: str = "") -> None:
        a = Assumption(
            agent=self.name,
            run_id=self.run_id,
            assumption=assumption,
            confidence=confidence,
            impact=impact,
            context=context,
        )
        log_assumption(a, self.run_id, OUTPUT_ROOT)
        self._logger.debug("Logged assumption [%s]: %s", impact, assumption)

    def _request_human_review(self, checkpoint: str, review_paths: list[str]) -> bool:
        """
        If HUMAN_REVIEW_ENABLED, post a review request and wait for approval.
        Returns True if approved or HITL disabled.
        """
        if not HUMAN_REVIEW_ENABLED:
            self._logger.info("HITL disabled — skipping checkpoint %s", checkpoint)
            return True

        self._logger.info("Requesting human review at checkpoint: %s", checkpoint)
        self._post(
            to_agent=AgentName.BROADCAST,
            message_type=MessageType.HUMAN_REVIEW_REQUEST,
            payload={"checkpoint": checkpoint, "review_paths": review_paths},
        )

        from shared.channel import wait_for_approval
        approved = wait_for_approval(self.run_id, checkpoint)
        if not approved:
            raise TimeoutError(f"Human review timed out at checkpoint {checkpoint}")
        self._logger.info("Human approved checkpoint: %s", checkpoint)
        return True

    def _read_prior_output(self, agent_name: str, filename: str) -> Path:
        """Return the path to a prior agent's output file, raising if missing."""
        path = OUTPUT_ROOT / self.run_id / agent_name / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Expected prior output not found: {path}\n"
                f"Ensure {agent_name} ran successfully before {self.name.value}."
            )
        return path
