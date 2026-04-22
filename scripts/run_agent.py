"""
scripts/run_agent.py
Run a single agent in isolation.

Usage:
    python scripts/run_agent.py --agent paper_analyst --run-id <id> --input paper.pdf
    python scripts/run_agent.py --agent formalizer --run-id <id>
    python scripts/run_agent.py --agent auditor_supervisor --run-id <id> --rerun
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.paper_analyst.agent import PaperAnalystAgent
from agents.formalizer.agent import FormalizerAgent
from agents.architect_developer.agent import ArchitectDeveloperAgent
from agents.auditor_supervisor.agent import AuditorSupervisorAgent

logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single pipeline agent")
    parser.add_argument(
        "--agent",
        required=True,
        choices=["paper_analyst", "formalizer", "architect_developer", "auditor_supervisor"],
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", help="Paper path (paper_analyst only)")
    parser.add_argument("--rerun", action="store_true", help="Re-run without clearing prior outputs")
    args = parser.parse_args()

    match args.agent:
        case "paper_analyst":
            if not args.input:
                print("--input is required for paper_analyst", file=sys.stderr)
                sys.exit(1)
            PaperAnalystAgent(run_id=args.run_id, paper_path=Path(args.input)).run()
        case "formalizer":
            FormalizerAgent(run_id=args.run_id).run()
        case "architect_developer":
            ArchitectDeveloperAgent(run_id=args.run_id).run()
        case "auditor_supervisor":
            AuditorSupervisorAgent(run_id=args.run_id).run()


if __name__ == "__main__":
    main()
