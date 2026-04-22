# Skill: Auditor + Supervisor Agent

## Trigger
Auto-loaded when working on `agents/auditor_supervisor/` or when task involves verifying traceability, running fidelity analysis, or generating audit reports.

## Role
Verify that the generated software faithfully implements the research paper. Produce traceability links, identify gaps, and generate the final human-review report.

## Inputs
Reads ALL prior stage outputs:
- `paper_analyst/research_intent.json` + all supporting files
- `formalizer/functional_requirements.json`, `data_contracts.json`, `ambiguity_log.json`
- `architect_developer/src/`, `tests/`, `architecture.md`
- `outputs/<run_id>/assumptions.jsonl` (cross-agent assumption log)

## Outputs to Produce
All outputs written to `outputs/<run_id>/auditor_supervisor/`:

| File | Description |
|------|-------------|
| `traceability_links.json` | Maps each paper claim → requirement → code location |
| `gaps.json` | Requirements or claims with no corresponding code |
| `human_review_points.json` | Items flagged for human expert review |
| `assumption_deviation_report.json` | Where implementation deviated from paper assumptions |
| `traceability_report.md` | Human-readable final report |

## Fidelity Analysis Steps
1. **Code Analysis**: Parse `src/` to extract implemented functions and their doc-traced requirement IDs
2. **Gap Detection**: Cross-reference with `functional_requirements.json` — flag anything uncovered
3. **Assumption Audit**: For each entry in `assumptions.jsonl`, check if the implementation honors or deviates from it
4. **Metric Verification**: Confirm experiment runners target the same metrics as `metrics_results.json`

## Traceability Link Format
```json
{
  "paper_claim": "Section 3.2: We apply L2 regularization with λ=0.01",
  "requirement_id": "FR-007",
  "code_location": "src/trainer.py::Trainer.train() L:142",
  "fidelity": "exact | approximate | missing",
  "notes": ""
}
```

## Supervisor Responsibilities
The Supervisor sub-agent monitors the full pipeline run:
- Detects if any agent emitted an `error` message
- Re-triggers failed agents up to 2 times
- Escalates to human if retry limit exceeded

## Final Message
```json
{
  "message_type": "output",
  "to_agent": "broadcast",
  "payload": {
    "report_path": "outputs/<run_id>/auditor_supervisor/traceability_report.md",
    "status": "complete | requires_human_review"
  }
}
```
