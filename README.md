# INDOT Erosion Control Agent

Deterministic, INDOT-first erosion control agent that reads project YAML, applies INDOT rules, retrieves citations from local resources, and outputs a Markdown report with recommendations, pay items, and traceability.

## Quick start

```bash
pip install -e .

ec_agent indot validate-resources --resources ./indot_resources
ec_agent indot build-index --resources ./indot_resources --index ./indot_index
ec_agent run --input examples/rural_widening.yaml --resources ./indot_resources --index ./indot_index --output report.md --no-llm
```

Outputs include temporary/permanent recommendations, INDOT citations or placeholders, pay item table, traceability matrix, clarifying questions, and missing INDOT resources.
