"""Shared input/output helpers for EC Agent."""

import json
import os
from pathlib import Path

import yaml

from ec_agent.models import ProjectInput
from ec_agent.rules_engine import Rule


def resolve_api_key(cli_value: str | None) -> str | None:
    """Resolve OpenAI API key from CLI, env var, or local file."""
    if cli_value:
        return cli_value

    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    key_file = os.getenv("OPENAI_API_KEY_FILE")
    key_path = Path(key_file) if key_file else Path("API_KEY") / "API_KEY.txt"
    if key_path.is_file():
        key = key_path.read_text(encoding="utf-8").strip()
        return key or None

    return None


def parse_project_text(project_text: str, project_format: str = "auto") -> ProjectInput:
    """Parse project YAML/JSON text into a ProjectInput model."""
    if not project_text.strip():
        raise ValueError("Project input is empty.")

    format_value = (project_format or "auto").lower()
    if format_value not in {"auto", "yaml", "yml", "json"}:
        raise ValueError("Project format must be auto, yaml, or json.")

    yaml_error = None
    if format_value in {"auto", "yaml", "yml"}:
        try:
            data = yaml.safe_load(project_text)
        except yaml.YAMLError as exc:
            if format_value != "auto":
                raise
            yaml_error = exc
        else:
            if not isinstance(data, dict):
                raise ValueError("Project input must be a mapping.")
            return ProjectInput(**data)

    try:
        data = json.loads(project_text)
    except json.JSONDecodeError as exc:
        if yaml_error:
            raise ValueError("Unable to parse project input as YAML or JSON.") from yaml_error
        raise ValueError("Unable to parse project input as JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Project input must be a JSON object.")
    return ProjectInput(**data)


def parse_rules_text(rules_text: str) -> list[Rule]:
    """Parse custom rules YAML into Rule models."""
    if not rules_text.strip():
        return []
    rules_data = yaml.safe_load(rules_text)
    if rules_data is None:
        return []
    if not isinstance(rules_data, dict):
        raise ValueError("Custom rules must be a YAML mapping with a 'rules' key.")
    rules_list = rules_data.get("rules")
    if not isinstance(rules_list, list):
        raise ValueError("Custom rules must define a list under the 'rules' key.")
    rules = [Rule(**rule_dict) for rule_dict in rules_list]
    rules.sort(key=lambda rule: rule.priority)
    return rules
