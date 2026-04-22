# Human-in-the-Loop (HITL) Checkpoints

## Overview
Human review acts as a cross-cutting control across all pipeline layers.
When `HUMAN_REVIEW_ENABLED=true`, the pipeline pauses at the following checkpoints.

## Checkpoints

### HITL-1: After Paper Analysis
**Agent**: `paper_analyst`
**Review**: Confirm extracted research questions, hypotheses, and method interpretations are correct before formalization begins.
**Artifacts to review**: `research_intent.json`, `domain_concepts.json`

### HITL-2: After Formalization
**Agent**: `formalizer`
**Review**: Validate data contracts/schemas, functional requirements, and the ambiguity log. Resolve flagged ambiguities before code generation.
**Artifacts to review**: `requirements.json`, `data_contracts.json`, `ambiguity_log.json`

### HITL-3: After Code Generation (optional, default OFF)
**Agent**: `architect_developer`
**Review**: Spot-check generated code and architecture for correctness.
**Artifacts to review**: `architecture.md`, `src/` directory

### HITL-4: Final Audit Report
**Agent**: `auditor_supervisor`
**Review**: Approve or reject the final traceability report before publication.
**Artifacts to review**: `traceability_report.md`, `assumption_deviation_report.json`

## Resuming After Review
After human approval, run:
```bash
python scripts/resume_pipeline.py --run-id <id> --checkpoint HITL-<n> --approved
```
