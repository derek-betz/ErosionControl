"""Shared input/output helpers for EC Agent."""

import base64
import binascii
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

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


def decode_base64_attachment(payload: dict[str, Any] | None) -> tuple[str, bytes] | None:
    """Decode a base64 attachment payload from the web UI."""
    if not payload:
        return None
    name = payload.get("name") or "attachment"
    data = payload.get("data")
    if not data:
        return None
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raw = base64.b64decode(data)
    return name, raw


def build_attachment_summary(
    ec_quantities: tuple[str, bytes] | None,
    plan_set_pdf: tuple[str, bytes] | None,
    plan_set_includes_ec_plans: bool | None = None,
) -> dict[str, Any]:
    """Build summary fields for attachments provided to the GUI."""
    summary: dict[str, Any] = {}
    if ec_quantities:
        summary.update(_summarize_ec_quantities(ec_quantities[0], ec_quantities[1]))
    if plan_set_pdf:
        summary.update(
            _summarize_plan_set_pdf(plan_set_pdf[0], plan_set_pdf[1], plan_set_includes_ec_plans)
        )
    return summary


def _summarize_ec_quantities(file_name: str, data: bytes) -> dict[str, Any]:
    summary: dict[str, Any] = {"ec_quantities_file": file_name}
    sheet_names = _extract_xlsx_sheet_names(data)
    if sheet_names:
        summary["ec_quantities_sheet_count"] = len(sheet_names)
        summary["ec_quantities_sheets"] = ", ".join(sheet_names)
    else:
        summary["ec_quantities_notice"] = "Unable to read sheet names."
    return summary


def _extract_xlsx_sheet_names(data: bytes) -> list[str]:
    if not data:
        return []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            workbook_xml = archive.read("xl/workbook.xml")
    except (zipfile.BadZipFile, KeyError):
        return []

    try:
        root = ElementTree.fromstring(workbook_xml)
    except ElementTree.ParseError:
        return []

    sheet_names = []
    for element in root.iter():
        if element.tag.endswith("sheet"):
            name = element.attrib.get("name")
            if name:
                sheet_names.append(name)
    return sheet_names


def _summarize_plan_set_pdf(
    file_name: str, data: bytes, has_ec_plans: bool | None
) -> dict[str, Any]:
    summary: dict[str, Any] = {"plan_set_pdf_file": file_name}
    page_count, notice = _extract_pdf_page_count(data)
    if page_count is not None:
        summary["plan_set_pdf_pages"] = page_count
    if has_ec_plans is not None:
        summary["plan_set_includes_ec_plans"] = has_ec_plans
    if notice:
        summary["plan_set_pdf_notice"] = notice
    return summary


def _extract_pdf_page_count(data: bytes) -> tuple[int | None, str | None]:
    if not data:
        return None, "Plan set PDF is empty."

    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        estimate = _estimate_pdf_page_count(data)
        if estimate:
            return estimate, "PDF page count estimated from raw content."
        return None, "Install pypdf for reliable PDF parsing."

    try:
        reader = PdfReader(io.BytesIO(data))
        return len(reader.pages), None
    except Exception:
        estimate = _estimate_pdf_page_count(data)
        if estimate:
            return estimate, "PDF page count estimated from raw content."
        return None, "Unable to read PDF page count."


def _estimate_pdf_page_count(data: bytes) -> int | None:
    if not data:
        return None
    page_tokens = data.count(b"/Type /Page")
    pages_token = data.count(b"/Type /Pages")
    estimate = page_tokens - pages_token
    if estimate <= 0:
        estimate = page_tokens
    return estimate or None
