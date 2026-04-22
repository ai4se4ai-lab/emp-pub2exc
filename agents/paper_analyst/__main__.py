"""
agents/paper_analyst/__main__.py
Entry point: python -m agents.paper_analyst --run-id <id> --input <paper_path>
"""
import argparse
import sys
from pathlib import Path

from agents.paper_analyst.agent import PaperAnalystAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper Analyst Agent")
    parser.add_argument("--run-id", required=True, help="Pipeline run ID")
    parser.add_argument("--input", required=True, help="Path to research paper (PDF or .txt)")
    args = parser.parse_args()

    paper_path = Path(args.input)
    if not paper_path.exists():
        print(f"Error: paper not found: {paper_path}", file=sys.stderr)
        sys.exit(1)

    agent = PaperAnalystAgent(run_id=args.run_id, paper_path=paper_path)
    agent.run()


if __name__ == "__main__":
    main()
