# Command: /project:run-pipeline

Run the full research-to-software pipeline on a paper.

## Usage
```
/project:run-pipeline <paper_path> [--skip-hitl] [--start-from <agent>]
```

## Steps
1. Validate `<paper_path>` exists and is PDF or text
2. Generate a new `run_id` (UUID4)
3. Create `outputs/<run_id>/` directory structure
4. Initialize `.comms/channel.jsonl` for this run
5. Execute agents in order:
   - `python -m agents.paper_analyst --run-id <id> --input <paper_path>`
   - `python -m agents.formalizer --run-id <id>`
   - `python -m agents.architect_developer --run-id <id>`
   - `python -m agents.auditor_supervisor --run-id <id>`
6. After each stage, check for HITL checkpoint unless `--skip-hitl` is set
7. Print final report path on completion

## Shell Execution
```bash
python scripts/run_pipeline.py "$ARGUMENTS"
```
