"""agents/architect_developer/__main__.py"""
import argparse
from agents.architect_developer.agent import ArchitectDeveloperAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Architect+Developer Agent")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    ArchitectDeveloperAgent(run_id=args.run_id).run()


if __name__ == "__main__":
    main()
