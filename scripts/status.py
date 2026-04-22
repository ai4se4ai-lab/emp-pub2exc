"""
scripts/status.py
View the communication channel status for a pipeline run.

Usage:
    python scripts/status.py --run-id <id>
    python scripts/status.py --run-id <id> --tail 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.channel import read_messages
from shared.message_schema import MessageType


STATUS_ICONS = {
    MessageType.OUTPUT: "✓",
    MessageType.STATUS: "→",
    MessageType.ERROR: "✗",
    MessageType.HUMAN_REVIEW_REQUEST: "⏸",
    MessageType.HUMAN_APPROVED: "✓✓",
    MessageType.REQUEST: "?",
    MessageType.RETRY: "↺",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="View pipeline status")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tail", type=int, default=50)
    args = parser.parse_args()

    messages = read_messages(run_id=args.run_id)
    if not messages:
        print(f"No messages found for run_id={args.run_id}")
        return

    messages = messages[-args.tail:]
    print(f"\nPipeline run: {args.run_id}")
    print(f"Messages: {len(messages)} (showing last {args.tail})\n")
    print(f"{'Time':<28} {'Icon':<4} {'From':<25} {'To':<25} {'Type':<25} Details")
    print("-" * 130)

    for msg in messages:
        icon = STATUS_ICONS.get(msg.message_type, " ")
        detail = ""
        if msg.error_detail:
            detail = f"ERROR: {msg.error_detail[:60]}"
        elif msg.payload:
            keys = list(msg.payload.keys())[:3]
            detail = ", ".join(keys)
        print(
            f"{msg.timestamp[:26]:<28} {icon:<4} {msg.from_agent:<25} "
            f"{msg.to_agent:<25} {msg.message_type:<25} {detail}"
        )

    # Summary
    errors = [m for m in messages if m.message_type == MessageType.ERROR]
    outputs = [m for m in messages if m.message_type == MessageType.OUTPUT]
    paused = [m for m in messages if m.message_type == MessageType.HUMAN_REVIEW_REQUEST]

    print(f"\nSummary: {len(outputs)} outputs | {len(errors)} errors | {len(paused)} pending reviews")


if __name__ == "__main__":
    main()
