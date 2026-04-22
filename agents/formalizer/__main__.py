"""
agents/formalizer/__main__.py
"""
import argparse
from agents.formalizer.agent import FormalizerAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Formalizer Agent")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    FormalizerAgent(run_id=args.run_id).run()


if __name__ == "__main__":
    main()
