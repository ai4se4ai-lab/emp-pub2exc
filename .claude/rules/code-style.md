# Code Style Rules

## Python
- Use `black` formatter, line length 100
- Type hints required on all function signatures
- Docstrings required for all public functions (Google style)
- Use `dataclasses` or `pydantic` for structured data, never raw dicts
- Prefer `pathlib.Path` over `os.path`

## Naming Conventions
- Agent classes: `{Name}Agent` (e.g., `PaperAnalystAgent`)
- Message types: `{Source}To{Target}Message` (e.g., `AnalystToFormalizerMessage`)
- Output files: `{run_id}_{agent}_{artifact}.json`

## Imports
- Standard lib first, then third-party, then local
- Use absolute imports within the project

## Error Handling
- All agent methods must catch and log exceptions before re-raising
- Validation errors must include the offending field and value
- Never silently swallow errors in agent communication
