"""
shared/channel.py
Communication channel for inter-agent messaging via a JSONL append log.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from shared.message_schema import AgentMessage, AgentName, MessageType, Assumption


CHANNEL_DIR = Path(".comms")
CHANNEL_FILE = CHANNEL_DIR / "channel.jsonl"


def _ensure_channel() -> None:
    CHANNEL_DIR.mkdir(exist_ok=True)
    if not CHANNEL_FILE.exists():
        CHANNEL_FILE.touch()


def post_message(message: AgentMessage) -> None:
    """Append a message to the shared channel."""
    _ensure_channel()
    with open(CHANNEL_FILE, "a") as f:
        f.write(message.model_dump_json() + "\n")


def read_messages(
    run_id: str | None = None,
    from_agent: AgentName | None = None,
    to_agent: AgentName | None = None,
    message_type: MessageType | None = None,
) -> list[AgentMessage]:
    """Read and optionally filter messages from the channel."""
    _ensure_channel()
    messages: list[AgentMessage] = []
    with open(CHANNEL_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = AgentMessage.model_validate_json(line)
            except Exception:
                continue
            if run_id and msg.run_id != run_id:
                continue
            if from_agent and msg.from_agent != from_agent:
                continue
            if to_agent and msg.to_agent not in (to_agent, AgentName.BROADCAST):
                continue
            if message_type and msg.message_type != message_type:
                continue
            messages.append(msg)
    return messages


def wait_for_approval(run_id: str, checkpoint: str, timeout_seconds: int = 300) -> bool:
    """
    Poll the channel for a human_approved message for the given checkpoint.
    Returns True if approved, False if timed out.
    """
    import time
    elapsed = 0
    interval = 5
    while elapsed < timeout_seconds:
        msgs = read_messages(run_id=run_id, message_type=MessageType.HUMAN_APPROVED)
        for m in msgs:
            if m.payload.get("checkpoint") == checkpoint:
                return True
        time.sleep(interval)
        elapsed += interval
    return False


def log_assumption(assumption: Assumption, run_id: str, output_root: Path) -> None:
    """Append an assumption to the cross-agent assumptions log."""
    log_path = output_root / run_id / "assumptions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(assumption.model_dump_json() + "\n")
