# EC Agent

[![CI](https://github.com/derek-betz/ErosionControl/workflows/CI/badge.svg)](https://github.com/derek-betz/ErosionControl/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**EC Agent** is an intelligent assistant for roadway engineers that generates erosion control (EC) practices and construction pay items based on project characteristics. It uses a deterministic YAML-based rules engine with optional LLM enhancement to provide traceable, standards-based recommendations.

## Features

- 🏗️ **Project-Based Analysis**: Input project data (slopes, soils, disturbed acres, drainage features, phasing, jurisdiction)
- 📋 **EC Practice Recommendations**: Generates temporary and permanent erosion control practices
- 💰 **Pay Item Generation**: Automatically creates construction pay items with quantity estimates
- 🔍 **Rule Traceability**: Every recommendation includes rule ID and source document references
- ⚙️ **YAML Rules Engine**: Deterministic, customizable rules for different jurisdictions and standards
- 🤖 **Optional LLM Enhancement**: OpenAI integration for additional insights and explanations
- 🖥️ **CLI Interface**: Easy-to-use command-line interface built with Typer
- **Web UI**: Local browser-based interface for running projects without the CLI
- **Desktop UI**: Tkinter app with file pickers for offline use
- ✅ **Type-Safe**: Full Pydantic model validation for inputs and outputs
- 🧪 **Well-Tested**: Comprehensive test suite with pytest

## Installation

### Requirements

- Python 3.12 or higher
- pip

### Install from source

```bash
# Clone the repository
git clone https://github.com/derek-betz/ErosionControl.git
cd ErosionControl

# Install in development mode
pip install -e .

# Or install with LLM support
pip install -e ".[llm]"

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Validate a Project Input

```bash
ec-agent validate examples/highway_project.yaml
```

### 2. Process a Project

```bash
ec-agent process examples/highway_project.yaml --output results.yaml
```

### 3. Use Custom Rules

```bash
ec-agent process examples/highway_project.yaml --rules examples/custom_rules.yaml --output results.yaml
```

### 4. Enable LLM Enhancement

```bash
export OPENAI_API_KEY=your-api-key
ec-agent process examples/highway_project.yaml --llm --output results.yaml
```

You can also set `OPENAI_API_KEY_FILE` to a key file path or place the key in
`API_KEY/API_KEY.txt` in your working directory.

### 5. Launch the Web UI (Optional)

```bash
ec-agent web
```

Open `http://127.0.0.1:8000` in your browser.

### 6. Launch the Desktop UI (Optional)

```bash
ec-agent desktop
```


## Project Input Format

Projects can be defined in YAML or JSON. Here's a minimal example:

```yaml
project_name: Highway 101 Widening
jurisdiction: California DOT
total_disturbed_acres: 5.2
predominant_soil: clay
predominant_slope: moderate
average_slope_percent: 18.5

drainage_features:
  - id: INLET-001
    type: inlet
    location: Station 10+50
    drainage_area_acres: 2.3

phases:
  - phase_id: PHASE-1
    name: Grading
    duration_days: 45
    disturbed_acres: 5.2
```

See `examples/` directory for complete examples.

## Output Format

The tool generates a detailed report with:

- **Temporary EC Practices**: Silt fence, inlet protection, construction entrance, etc.
- **Permanent EC Practices**: Permanent seeding, erosion control blankets, etc.
- **Pay Items**: Construction pay items with quantities and estimated costs
- **Rule Traceability**: Each practice includes the rule ID and source document
- **Summary Statistics**: Total practices, pay items, and estimated costs

Example output:

```yaml
project_name: Highway 101 Widening
timestamp: '2024-01-15T10:30:00'
temporary_practices:
  - practice_type: silt_fence
    is_temporary: true
    quantity: 1040.0
    unit: LF
    location: Perimeter of disturbed area
    rule_id: SILT_FENCE_001
    rule_source: EPA NPDES CGP
    justification: Perimeter sediment control per EPA NPDES requirements
pay_items:
  - item_number: EC-001
    description: Silt Fence, Type A
    quantity: 1040.0
    unit: LF
    estimated_unit_cost: 3.50
    ec_practice_ref: silt_fence_SILT_FENCE_001
    rule_id: SILT_FENCE_001
    rule_source: EPA NPDES CGP
summary:
  total_temporary_practices: 4
  total_permanent_practices: 1
  total_pay_items: 5
  total_estimated_cost: 7890.50
```

## Custom Rules

Create custom rules for your jurisdiction or project requirements:

```yaml
rules:
  - id: CUSTOM_001
    name: Custom Silt Fence Rule
    source: Local County Standards
    priority: 10
    conditions:
      - field: total_disturbed_acres
        operator: gt
        value: 1.0
    action:
      practice_type: silt_fence
      is_temporary: true
      quantity_formula: total_disturbed_acres * 250
      unit: LF
      location_template: Site perimeter
      justification: County-specific perimeter control
      pay_item_number: EC-001
      pay_item_description: Silt Fence
      estimated_unit_cost: 4.00
```

## CLI Commands

### `process`

Process a project and generate EC recommendations.

```bash
ec-agent process [OPTIONS] INPUT_FILE
```

**Options:**
- `--output, -o PATH`: Output file path (YAML or JSON)
- `--rules, -r PATH`: Custom rules file
- `--llm/--no-llm`: Enable/disable LLM enhancement
- `--llm-api-key TEXT`: OpenAI API key
- `--quiet, -q`: Suppress console output

### `validate`

Validate a project input file.

```bash
ec-agent validate INPUT_FILE
```

### `web`

Launch the local web UI.

```bash
ec-agent web --host 127.0.0.1 --port 8000 --open
```

### `desktop`

Launch the desktop UI.

```bash
ec-agent desktop
```

### `version`

Show version information.

```bash
ec-agent version
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=ec_agent --cov-report=html

# Run linter
ruff check src/ tests/

# Format code
ruff format src/ tests/
```

### Project Structure

```
ErosionControl/
├── src/ec_agent/
│   ├── __init__.py
│   ├── models.py          # Pydantic data models
│   ├── rules_engine.py    # YAML rules engine
│   ├── llm_adapter.py     # Optional LLM enhancement
│   ├── cli.py             # Typer CLI
│   ├── io_utils.py        # Shared input/output helpers
│   ├── desktop_app.py     # Desktop UI (Tkinter)
│   └── web_app.py         # Local web UI server
├── tests/
│   ├── test_models.py
│   ├── test_rules_engine.py
│   ├── test_llm_adapter.py
│   └── test_integration.py
├── examples/
│   ├── highway_project.yaml
│   ├── residential_project.json
│   └── custom_rules.yaml
├── pyproject.toml
└── README.md
```

## Architecture

### Rules Engine

The rules engine is deterministic and operates in three phases:

1. **Condition Evaluation**: Check if project characteristics match rule conditions
2. **Quantity Calculation**: Calculate practice quantities using formulas
3. **Output Generation**: Create EC practices and pay items with full traceability

### LLM Adapter

The optional LLM adapter:
- Enhances recommendations with context-aware insights
- Provides detailed explanations for EC practices
- Maintains full traceability to the base rules engine
- Gracefully degrades if LLM is unavailable

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass and code is formatted
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [Pydantic](https://docs.pydantic.dev/) for data validation
- CLI powered by [Typer](https://typer.tiangolo.com/)
- Testing with [pytest](https://pytest.org/)
- Code quality with [Ruff](https://docs.astral.sh/ruff/)

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
