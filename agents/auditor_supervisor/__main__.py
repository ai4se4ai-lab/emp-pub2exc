"""agents/auditor_supervisor/__main__.py"""
import argparse
from agents.auditor_supervisor.agent import AuditorSupervisorAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditor+Supervisor Agent")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    AuditorSupervisorAgent(run_id=args.run_id).run()


if __name__ == "__main__":
    main()
