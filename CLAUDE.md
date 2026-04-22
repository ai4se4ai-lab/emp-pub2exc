# Research-to-Software Agentic Framework

## Project Overview
This framework transforms academic research publications into traceable, production-ready software using a multi-agent pipeline. Four specialized agent layers work together through a shared communication channel.

## Architecture
```
Paper Publication
       ↓
[Paper Analyst Agent]      → Research Intent, Questions, Methods, Datasets
       ↓
[Formalizer + Requirements Agent] → Ontology, Data Contracts, Assumptions
       ↓
[Architect + Developer + Test Agents] → Architecture, Code, Tests, Deployment
       ↓
[Auditor + Supervisor Agent]  → Traceability, Fidelity Analysis, Report
```

## Tech Stack
- **Language**: Python 3.11+
- **Agent Communication**: Shared JSON message bus (`.comms/channel.jsonl`)
- **LLM Backend**: Anthropic Claude API (`claude-sonnet-4-20250514`)
- **Orchestration**: `scripts/run_pipeline.py`
- **Output Artifacts**: `outputs/` directory per run

## Agent Roles
| Agent | Layer | Input | Output |
|-------|-------|-------|--------|
| `paper_analyst` | Paper Understanding | PDF/paper | Research intent JSON |
| `formalizer` | Formalization | Research intent | Requirements + data contracts |
| `architect_developer` | Software Synthesis | Requirements | Code, tests, deployment config |
| `auditor_supervisor` | Verification | All artifacts | Traceability report |

## Commands
- `python scripts/run_pipeline.py --paper <path>` — Run full pipeline
- `python scripts/run_agent.py --agent <name> --input <path>` — Run single agent
- `python scripts/status.py` — View communication channel status
- `python scripts/audit.py --run-id <id>` — Generate audit report

## Coding Conventions
- All inter-agent messages must use `shared/message_schema.py` types
- Each agent reads from and writes to `outputs/<run_id>/<agent_name>/`
- Agents must log assumptions to `outputs/<run_id>/assumptions.jsonl`
- Human-in-the-loop checkpoints are defined in `.claude/rules/hitl.md`
- Never hardcode API keys — use environment variables

## Environment Variables
```
ANTHROPIC_API_KEY=your_key_here
PIPELINE_LOG_LEVEL=INFO
HUMAN_REVIEW_ENABLED=true
```
