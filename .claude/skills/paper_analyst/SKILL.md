# Skill: Paper Analyst Agent

## Trigger
Auto-loaded when working on `agents/paper_analyst/` or when task involves extracting structured information from a research publication.

## Role
Transform a raw research PDF into a structured `ResearchIntent` object. This is the entry point of the entire pipeline.

## Outputs to Produce
All outputs written to `outputs/<run_id>/paper_analyst/`:

| File | Description |
|------|-------------|
| `research_intent.json` | Top-level structured intent object |
| `research_questions.json` | List of extracted RQs and hypotheses |
| `domain_concepts.json` | Key domain terms, definitions, and assumptions |
| `methods_models.json` | Algorithms, models, experimental design |
| `datasets.json` | Datasets, splits, preprocessing described |
| `metrics_results.json` | Evaluation metrics and reported results |

## Extraction Strategy
1. Parse full paper text (title, abstract, sections)
2. Use GenAI to extract each output category separately — do NOT try to extract everything in one prompt
3. Cross-reference: ensure methods align with datasets and metrics
4. Flag any ambiguities in `domain_concepts.json` under `"ambiguous": true`

## Key Prompt Patterns
- Always include paper title + abstract in every extraction prompt for context
- Ask for confidence scores on each extracted item
- For methods: extract both the described method AND implementation hints

## Message to Emit
After completion, post to channel:
```json
{
  "message_type": "output",
  "to_agent": "formalizer",
  "payload": { "research_intent_path": "outputs/<run_id>/paper_analyst/research_intent.json" }
}
```
