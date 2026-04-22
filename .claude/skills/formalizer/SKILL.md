# Skill: Formalizer + Requirements Agent

## Trigger
Auto-loaded when working on `agents/formalizer/` or when task involves converting research intent into formal software specifications.

## Role
Transform `ResearchIntent` (from Paper Analyst) into formal software artifacts:
- Ontology / concept model
- Functional requirements
- Data contracts / schemas
- Assumptions and ambiguity log

## Inputs
Reads from `outputs/<run_id>/paper_analyst/` — specifically `research_intent.json` and `domain_concepts.json`.

## Outputs to Produce
All outputs written to `outputs/<run_id>/formalizer/`:

| File | Description |
|------|-------------|
| `concept_model.json` | Ontology: entities, relationships, cardinalities |
| `functional_requirements.json` | Numbered list of FRs with priority and source tracing |
| `data_contracts.json` | JSON Schema definitions for all data structures |
| `ambiguity_log.json` | Flagged ambiguities with severity and resolution options |

## Formalization Rules
- Every functional requirement must trace back to a research question ID from `research_questions.json`
- Data contracts must be valid JSON Schema Draft-07
- Ambiguities with `severity: "high"` MUST block pipeline until human resolved (see `hitl.md`)
- The concept model must include all entities referenced in methods and datasets

## Ontology Development Strategy
1. Seed entities from `domain_concepts.json`
2. Derive relationships from methods and experimental setup
3. Validate completeness: every dataset field maps to a schema property

## Message to Emit
```json
{
  "message_type": "output",
  "to_agent": "architect_developer",
  "payload": {
    "requirements_path": "outputs/<run_id>/formalizer/functional_requirements.json",
    "data_contracts_path": "outputs/<run_id>/formalizer/data_contracts.json"
  }
}
```
