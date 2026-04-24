"""
scripts/run_agent.py
Run a single agent in isolation.

Usage:
    python scripts/run_agent.py --agent paper_analyst --run-id <id> --input paper.pdf
    python scripts/run_agent.py --agent paper_analyst --run-id <id> --example-dir tests/examples/KGTN-en
    python scripts/run_agent.py --agent formalizer --run-id <id>
    python scripts/run_agent.py --agent auditor_supervisor --run-id <id> --rerun
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.llm_client import load_env_file
load_env_file()

from agents.paper_analyst.agent import PaperAnalystAgent
from agents.formalizer.agent import FormalizerAgent
from agents.architect_developer.agent import ArchitectDeveloperAgent
from agents.auditor_supervisor.agent import AuditorSupervisorAgent
from shared.example_utils import resolve_example_context

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
    parser.add_argument("--example-dir", help="Example directory containing a single Markdown paper")
    parser.add_argument("--rerun", action="store_true", help="Re-run without clearing prior outputs")
    args = parser.parse_args()

    match args.agent:
        case "paper_analyst":
            if not args.input and not args.example_dir:
                print("--input or --example-dir is required for paper_analyst", file=sys.stderr)
                sys.exit(1)
            paper_path = (
                resolve_example_context(args.example_dir).paper_path
                if args.example_dir
                else Path(args.input)
            )
            PaperAnalystAgent(run_id=args.run_id, paper_path=paper_path).run()
        case "formalizer":
            FormalizerAgent(run_id=args.run_id).run()
        case "architect_developer":
            ArchitectDeveloperAgent(run_id=args.run_id).run()
        case "auditor_supervisor":
            AuditorSupervisorAgent(run_id=args.run_id).run()


if __name__ == "__main__":
    main()
