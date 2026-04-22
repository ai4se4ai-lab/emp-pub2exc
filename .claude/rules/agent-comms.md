# Agent Communication Rules

## Communication Channel
All agents communicate through `.comms/channel.jsonl` — a newline-delimited JSON log.

## Message Format
Every message MUST conform to `shared/message_schema.py::AgentMessage`:
```json
{
  "run_id": "uuid4",
  "timestamp": "ISO8601",
  "from_agent": "paper_analyst | formalizer | architect_developer | auditor_supervisor",
  "to_agent": "paper_analyst | formalizer | architect_developer | auditor_supervisor | broadcast",
  "message_type": "output | request | status | error | human_review_request",
  "payload": { ... },
  "artifact_refs": ["relative/path/to/output/file.json"]
}
```

## Agent Execution Order (Default Pipeline)
1. `paper_analyst` → reads paper, emits `ResearchIntent`
2. `formalizer` → reads `ResearchIntent`, emits `Requirements + DataContracts`
3. `architect_developer` → reads requirements, emits `Code + Tests + DeploymentConfig`
4. `auditor_supervisor` → reads all artifacts, emits `TraceabilityReport`

## Broadcast Messages
Agents may broadcast status updates to all agents using `to_agent: "broadcast"`.

## Blocking on Human Review
If `HUMAN_REVIEW_ENABLED=true`, agents must pause and emit `message_type: "human_review_request"` at checkpoints defined in `hitl.md`. They must not proceed until a `human_approved` message is received.

## Assumptions Logging
Any assumption an agent makes must be appended to `outputs/<run_id>/assumptions.jsonl` with:
- `agent`, `assumption`, `confidence` (0.0–1.0), `impact` (low/medium/high)
