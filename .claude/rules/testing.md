# Testing Rules

## Framework
- Use `pytest` for all tests
- Tests live in `tests/{agent_name}/` mirroring `agents/` structure
- Fixtures in `tests/conftest.py`

## Coverage Requirements
- All agent `run()` methods: 100% coverage
- Message schema validation: 100% coverage
- Communication channel read/write: 100% coverage
- Minimum overall: 80%

## Test Types
- **Unit**: Test each agent method in isolation with mocked LLM responses
- **Integration**: Test agent-to-agent handoff with fixture inputs
- **End-to-end**: `tests/e2e/test_full_pipeline.py` runs a mini paper through the full pipeline

## Mocking LLM Calls
Use `tests/fixtures/mock_responses/` for canned LLM responses. Never call the real API in tests unless in a dedicated `tests/e2e/` suite with `@pytest.mark.e2e`.

## Running Tests
```bash
pytest tests/ -v --cov=agents --cov=shared
pytest tests/e2e/ -m e2e  # requires ANTHROPIC_API_KEY
```
