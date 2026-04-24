# Skill: Architect + Developer + Test Agents

## Trigger
Auto-loaded when working on `agents/architect_developer/` or when task involves generating software architecture, code, tests, or deployment configs from requirements.

## Role
Transform formal requirements and data contracts into runnable, tested software.

## Sub-Agents Within This Layer
This layer uses three sequential sub-agents internally:

### 1. Architect Sub-Agent
- Input: `functional_requirements.json`, `concept_model.json`
- Output: `architecture.md` — describes modules, interfaces, and dependencies
- Output: `modules.json` — machine-readable module list with responsibilities

### 2. Developer Sub-Agent
- Input: `architecture.md`, `data_contracts.json`
- Output: `src/` — Python source files implementing the architecture
- Output: `api_spec.json` — OpenAPI-style spec for any exposed interfaces

### 3. Test Sub-Agent
- Input: `src/`, `functional_requirements.json`
- Output: `tests/` — pytest test files with ≥80% coverage target
- Output: `experiment_runners/` — scripts to reproduce paper experiments

## Code Generation Rules
- Each module must have a docstring tracing it to requirement IDs: `# Implements: FR-001, FR-003`
- Use data contract schemas to generate `pydantic` models automatically
- Tests must cover both happy path and edge cases identified in `ambiguity_log.json`
- Experiment runners must match the exact dataset splits from `datasets.json`

## Deployment Output
- `Dockerfile` with reproducible build
- `requirements.txt` pinned versions
- `deployment_config.json` with environment variables and resource requirements
- Deployment config should include provider-agnostic LLM settings so generated software can run with Anthropic, OpenAI, or Ollama backends

## Message to Emit
```json
{
  "message_type": "output",
  "to_agent": "auditor_supervisor",
  "payload": {
    "src_path": "outputs/<run_id>/architect_developer/src/",
    "tests_path": "outputs/<run_id>/architect_developer/tests/",
    "architecture_path": "outputs/<run_id>/architect_developer/architecture.md"
  }
}
```
