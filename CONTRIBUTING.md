# Contributing to EC Agent

Thank you for your interest in contributing to EC Agent! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/ErosionControl.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install development dependencies: `pip install -e ".[dev]"`

## Development Setup

```bash
# Install the package in editable mode with dev dependencies
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

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Line length is limited to 100 characters
- Use type hints for function parameters and return values
- Follow PEP 8 style guidelines
- Write docstrings for all public functions, classes, and modules

## Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting a PR
- Aim for high test coverage (>80%)
- Use pytest fixtures for common test data
- Test both success and failure cases

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in the present tense (e.g., "Add", "Fix", "Update")
- Keep the first line under 72 characters
- Add a detailed description if necessary

## Pull Request Process

1. Update the README.md if your changes add new features or change behavior
2. Ensure all tests pass and linting is clean
3. Update the version number in `pyproject.toml` if applicable
4. Submit your PR with a clear description of the changes
5. Link any related issues in the PR description

## Adding New Features

### Adding New Rules

To add new default rules, edit `src/ec_agent/rules_engine.py` in the `_load_default_rules()` method:

```python
{
    "id": "UNIQUE_RULE_ID",
    "name": "Descriptive Rule Name",
    "source": "Source Document/Standard",
    "priority": 10,  # Lower number = higher priority
    "conditions": [
        {"field": "field_name", "operator": "gt", "value": 1.0}
    ],
    "action": {
        "practice_type": "practice_type_name",
        "is_temporary": True,
        "quantity_formula": "total_disturbed_acres * 100",
        "unit": "LF",
        "location_template": "Location description",
        "justification": "Why this practice is needed",
        "pay_item_number": "EC-XXX",
        "pay_item_description": "Pay item name",
        "estimated_unit_cost": 5.00
    }
}
```

### Adding New EC Practice Types

To add new erosion control practice types, edit `src/ec_agent/models.py` in the `ECPracticeType` enum:

```python
class ECPracticeType(str, Enum):
    # ... existing types ...
    NEW_PRACTICE_TYPE = "new_practice_type"
```

### Adding New Soil or Slope Types

Edit the `SoilType` or `SlopeType` enums in `src/ec_agent/models.py`:

```python
class SoilType(str, Enum):
    # ... existing types ...
    NEW_SOIL_TYPE = "new_soil_type"
```

## Bug Reports

When reporting bugs, please include:
- A clear description of the issue
- Steps to reproduce the problem
- Expected behavior
- Actual behavior
- Your environment (OS, Python version, EC Agent version)
- Any relevant error messages or logs

## Feature Requests

We welcome feature requests! Please:
- Check if the feature has already been requested
- Clearly describe the feature and its use case
- Explain how it would benefit users
- Provide examples if possible

## Questions

If you have questions about contributing, please:
- Check the README.md documentation first
- Search existing issues for similar questions
- Open a new issue with the "question" label

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive criticism
- Assume good intentions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
