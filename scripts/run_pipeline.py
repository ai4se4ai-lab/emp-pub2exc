"""
scripts/run_pipeline.py
Orchestrates the full research-to-software pipeline.

Usage:
    python scripts/run_pipeline.py --paper path/to/paper.pdf
    python scripts/run_pipeline.py --paper path/to/paper.pdf --skip-hitl
    python scripts/run_pipeline.py --paper path/to/paper.pdf --start-from formalizer
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.paper_analyst.agent import PaperAnalystAgent
from agents.formalizer.agent import FormalizerAgent
from agents.architect_developer.agent import ArchitectDeveloperAgent
from agents.auditor_supervisor.agent import AuditorSupervisorAgent

logging.basicConfig(
    level=os.getenv("PIPELINE_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")

AGENT_ORDER = ["paper_analyst", "formalizer", "architect_developer", "auditor_supervisor"]


def run_pipeline(paper_path: Path, skip_hitl: bool, start_from: str) -> str:
    run_id = str(uuid.uuid4())
    logger.info("=" * 60)
    logger.info("Pipeline run started | run_id=%s", run_id)
    logger.info("Paper: %s", paper_path)
    logger.info("HITL: %s", "disabled" if skip_hitl else "enabled")
    logger.info("=" * 60)

    if skip_hitl:
        os.environ["HUMAN_REVIEW_ENABLED"] = "false"

    # Initialize comms channel for this run
    Path(".comms").mkdir(exist_ok=True)

    start_idx = AGENT_ORDER.index(start_from) if start_from in AGENT_ORDER else 0

    agents = {
        "paper_analyst": lambda: PaperAnalystAgent(run_id=run_id, paper_path=paper_path),
        "formalizer": lambda: FormalizerAgent(run_id=run_id),
        "architect_developer": lambda: ArchitectDeveloperAgent(run_id=run_id),
        "auditor_supervisor": lambda: AuditorSupervisorAgent(run_id=run_id),
    }

    for agent_name in AGENT_ORDER[start_idx:]:
        logger.info("--- Running agent: %s ---", agent_name)
        try:
            agents[agent_name]().run()
            logger.info("--- Agent complete: %s ---", agent_name)
        except Exception as e:
            logger.error("Agent %s failed: %s", agent_name, e)
            logger.error("Pipeline halted at stage: %s", agent_name)
            logger.error("To retry from this stage: --start-from %s --paper %s", agent_name, paper_path)
            sys.exit(1)

    report_path = Path("outputs") / run_id / "auditor_supervisor" / "traceability_report.md"
    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info("Run ID: %s", run_id)
    logger.info("Report: %s", report_path)
    logger.info("=" * 60)
    return run_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-to-Software Pipeline")
    parser.add_argument("--paper", required=True, help="Path to research paper (PDF or .txt)")
    parser.add_argument("--skip-hitl", action="store_true", help="Skip human-in-the-loop checkpoints")
    parser.add_argument(
        "--start-from",
        choices=AGENT_ORDER,
        default="paper_analyst",
        help="Resume pipeline from a specific agent stage",
    )
    args = parser.parse_args()

    paper_path = Path(args.paper)
    if not paper_path.exists():
        print(f"Error: paper file not found: {paper_path}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(paper_path, args.skip_hitl, args.start_from)


if __name__ == "__main__":
    main()
