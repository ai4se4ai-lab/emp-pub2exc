# Command: /project:audit

Re-run the auditor agent on an existing pipeline run to regenerate the traceability report.

## Usage
```
/project:audit <run_id>
```

## Steps
1. Verify `outputs/<run_id>/` exists and contains prior stage outputs
2. Run auditor in isolation: `python -m agents.auditor_supervisor --run-id <run_id> --rerun`
3. Output new report to `outputs/<run_id>/auditor_supervisor/traceability_report_<timestamp>.md`

## Shell Execution
```bash
python scripts/run_agent.py --agent auditor_supervisor --run-id "$ARGUMENTS" --rerun
```
