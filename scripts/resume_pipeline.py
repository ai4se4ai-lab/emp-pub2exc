"""
scripts/resume_pipeline.py
Resume a paused pipeline after human review approval.

Usage:
    python scripts/resume_pipeline.py --run-id <id> --checkpoint HITL-1 --approved
    python scripts/resume_pipeline.py --run-id <id> --checkpoint HITL-2 --rejected --reason "..."
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.channel import post_message
from shared.message_schema import AgentMessage, AgentName, MessageType

CHECKPOINT_TO_NEXT_AGENT = {
    "HITL-1": "formalizer",
    "HITL-2": "architect_developer",
    "HITL-3": "auditor_supervisor",
    "HITL-4": None,  # End of pipeline
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume pipeline after human review")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--checkpoint", required=True, choices=list(CHECKPOINT_TO_NEXT_AGENT))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--approved", action="store_true")
    group.add_argument("--rejected", action="store_true")
    parser.add_argument("--reason", default="", help="Notes on approval or rejection")
    args = parser.parse_args()

    msg_type = MessageType.HUMAN_APPROVED if args.approved else MessageType.ERROR
    msg = AgentMessage(
        run_id=args.run_id,
        from_agent=AgentName.BROADCAST,
        to_agent=AgentName.BROADCAST,
        message_type=msg_type,
        payload={
            "checkpoint": args.checkpoint,
            "approved": args.approved,
            "reason": args.reason,
            "reviewer_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    post_message(msg)

    if args.approved:
        next_agent = CHECKPOINT_TO_NEXT_AGENT[args.checkpoint]
        print(f"✓ Approved checkpoint {args.checkpoint}.")
        if next_agent:
            print(f"  The pipeline will now continue with: {next_agent}")
            print(f"  Run: python scripts/run_agent.py --agent {next_agent} --run-id {args.run_id}")
        else:
            print("  Pipeline is complete.")
    else:
        print(f"✗ Rejected at checkpoint {args.checkpoint}. Reason: {args.reason}")
        print("  Review the artifacts and fix issues before re-running the failed stage.")


if __name__ == "__main__":
    main()
