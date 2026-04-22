# emp-pub2exc Agentic Framework

An agentic pipeline that transforms academic research publications into traceable, production-ready software. Four specialized AI agents collaborate through a shared communication channel, each building on the outputs of the previous stage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Research Publication (PDF)                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Paper Analyst Agent          [Paper Understanding Layer]        │
│  • Extracts research questions, hypotheses                       │
│  • Maps domain concepts, methods, datasets, metrics             │
│  Output: research_intent.json, domain_concepts.json, ...        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼ HITL-1 (human review)
┌─────────────────────────────────────────────────────────────────┐
│  Formalizer + Requirements Agent   [Formalization Layer]         │
│  • Builds ontology / concept model                              │
│  • Derives traceable functional requirements (FR-XXX)           │
│  • Generates JSON Schema data contracts                         │
│  • Logs ambiguity log                                           │
│  Output: functional_requirements.json, data_contracts.json, ... │
└────────────────────────────┬────────────────────────────────────┘
                             ▼ HITL-2 (human review)
┌─────────────────────────────────────────────────────────────────┐
│  Architect + Developer + Test Agents  [Software Synthesis Layer] │
│  Phase 1 – Architecture: modules, interfaces, dependency graph  │
│  Phase 2 – Code: Python source with FR traceability comments    │
│  Phase 3 – Tests + Deployment: pytest suite, Dockerfile         │
│  Output: src/, tests/, architecture.md, Dockerfile, ...        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Auditor + Supervisor Agent   [Verification & Traceability]      │
│  • Builds paper-to-code traceability links                      │
│  • Detects gaps (missing requirements)                          │
│  • Generates assumption deviation report                        │
│  • Produces human-readable traceability_report.md              │
│  Output: traceability_report.md, gaps.json, ...                │
└────────────────────────────┬────────────────────────────────────┘
                             ▼ HITL-4 (human review)
                    Final Approved Report
```

**Cross-cutting controls**: Human-in-the-loop checkpoints (HITL-1 through HITL-4) and a shared assumptions log act at every layer.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-org/emp-pub2exc.git
cd emp-pub2exc
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 3. Run the full pipeline

```bash
python scripts/run_pipeline.py --paper path/to/paper.pdf
```

To skip human review checkpoints (fast mode):
```bash
python scripts/run_pipeline.py --paper path/to/paper.pdf --skip-hitl
```

---

## Repository Structure

```
emp-pub2exc/
├── CLAUDE.md                        # Claude Code project context
├── .mcp.json                        # MCP server integrations
├── .claude/
│   ├── settings.json                # Tool permissions & hooks
│   ├── rules/
│   │   ├── agent-comms.md           # Inter-agent messaging rules
│   │   ├── code-style.md            # Python style conventions
│   │   ├── hitl.md                  # Human-in-the-loop checkpoints
│   │   └── testing.md               # Test requirements
│   ├── skills/
│   │   ├── paper_analyst/SKILL.md   # Paper Analyst skill guide
│   │   ├── formalizer/SKILL.md      # Formalizer skill guide
│   │   ├── architect_developer/SKILL.md
│   │   └── auditor_supervisor/SKILL.md
│   ├── agents/
│   │   ├── paper-analyst.md         # Sub-agent definition
│   │   ├── formalizer.md
│   │   ├── architect-developer.md
│   │   └── auditor-supervisor.md
│   └── commands/
│       ├── run-pipeline.md          # /project:run-pipeline
│       └── audit.md                 # /project:audit
├── agents/
│   ├── paper_analyst/agent.py
│   ├── formalizer/agent.py
│   ├── architect_developer/agent.py
│   └── auditor_supervisor/agent.py
├── shared/
│   ├── base_agent.py                # Abstract base with HITL, logging
│   ├── channel.py                   # JSONL communication bus
│   ├── llm_client.py                # Anthropic API wrapper
│   └── message_schema.py            # Pydantic message types
├── scripts/
│   ├── run_pipeline.py              # Full pipeline orchestrator
│   ├── run_agent.py                 # Single-agent runner
│   ├── resume_pipeline.py           # Post-HITL resume
│   └── status.py                    # Channel status viewer
├── tests/
│   ├── conftest.py
│   ├── shared/
│   │   ├── test_message_schema.py
│   │   └── test_channel.py
│   └── agents/
│       └── test_paper_analyst.py
├── outputs/                         # Generated per run (gitignored)
└── .comms/                          # Message bus (gitignored)
```

---

## Agent Communication

All agents communicate through `.comms/channel.jsonl` — a shared append-only log.

```json
{
  "run_id": "uuid4",
  "from_agent": "paper_analyst",
  "to_agent": "formalizer",
  "message_type": "output",
  "payload": { "research_intent_path": "outputs/.../research_intent.json" },
  "artifact_refs": ["outputs/.../research_intent.json"]
}
```

View live pipeline status:
```bash
python scripts/status.py --run-id <your-run-id>
```

---

## Human-in-the-Loop Checkpoints

| Checkpoint | After Agent | Review Artifacts |
|-----------|-------------|-----------------|
| HITL-1 | Paper Analyst | `research_intent.json`, `domain_concepts.json` |
| HITL-2 | Formalizer | `functional_requirements.json`, `ambiguity_log.json` |
| HITL-3 | Architect+Dev *(optional)* | `architecture.md`, `src/` |
| HITL-4 | Auditor | `traceability_report.md`, `gaps.json` |

After reviewing artifacts, approve or reject:
```bash
python scripts/resume_pipeline.py --run-id <id> --checkpoint HITL-2 --approved
python scripts/resume_pipeline.py --run-id <id> --checkpoint HITL-2 --rejected --reason "ambiguities unresolved"
```

---

## Running Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=agents --cov=shared   # with coverage
pytest tests/e2e/ -m e2e                      # end-to-end (requires API key)
```

---

## Claude Code Integration

This project is optimized for use with [Claude Code](https://claude.ai/code). Skills are auto-loaded per task context:

- Working in `agents/paper_analyst/` → loads `.claude/skills/paper_analyst/SKILL.md`
- Working in `agents/formalizer/` → loads `.claude/skills/formalizer/SKILL.md`
- etc.

Custom slash commands available in Claude Code:
- `/project:run-pipeline <paper_path>` — run the full pipeline
- `/project:audit <run_id>` — re-run audit on existing outputs

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `PIPELINE_LOG_LEVEL` | `INFO` | Log verbosity |
| `HUMAN_REVIEW_ENABLED` | `true` | Enable HITL checkpoints |
| `OUTPUT_ROOT` | `outputs` | Where run artifacts are stored |

---

## Contributing

1. Follow `.claude/rules/code-style.md` for all Python
2. Every new feature needs tests in `tests/`
3. Agent changes must update the corresponding `SKILL.md`
4. All inter-agent messages must use `shared/message_schema.py` types
