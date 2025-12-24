from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_rules(path: str | Path) -> List[Dict[str, Any]]:
    """Load YAML rule definitions."""
    raw = yaml.safe_load(Path(path).read_text()) or []
    return raw


def _resolve(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str) and value in context:
        return context[value]
    return value


def evaluate_condition(condition: Any, context: Dict[str, Any]) -> bool:
    """Evaluate a JSONLogic-lite condition dict."""
    if condition is None:
        return True
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, dict):
        return bool(condition)

    if "and" in condition:
        return all(evaluate_condition(c, context) for c in condition["and"])
    if "or" in condition:
        return any(evaluate_condition(c, context) for c in condition["or"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], context)

    def cmp(op: str, items: List[Any]) -> bool:
        left = _resolve(items[0], context)
        right = _resolve(items[1], context)
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        if op == "gt":
            return left is not None and right is not None and left > right
        if op == "lt":
            return left is not None and right is not None and left < right
        if op == "gte":
            return left is not None and right is not None and left >= right
        if op == "lte":
            return left is not None and right is not None and left <= right
        raise ValueError(f"Unsupported comparison {op}")

    for op in ("eq", "ne", "gt", "lt", "gte", "lte"):
        if op in condition:
            return cmp(op, condition[op])

    if "in" in condition:
        key, arr = condition["in"]
        val = _resolve(key, context)
        return val in arr
    if "contains" in condition:
        arr, key = condition["contains"]
        arr_val = _resolve(arr, context) or []
        return key in arr_val
    if "exists" in condition:
        key = condition["exists"]
        return _resolve(key, context) is not None
    if "missing" in condition:
        key = condition["missing"]
        return _resolve(key, context) is None
    if "between" in condition:
        value, bounds = condition["between"]
        target = _resolve(value, context)
        low, high = bounds
        return target is not None and low <= target <= high

    raise ValueError(f"Unsupported condition {condition}")


def apply_rules(context: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return rules that apply to the context."""
    applied = []
    for rule in rules:
        if evaluate_condition(rule.get("conditions"), context):
            applied.append(rule)
    return applied


def generate_recommendations(
    context: Dict[str, Any], rules: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for rule in apply_rules(context, rules):
        results.append(
            {
                "rule_id": rule["id"],
                "title": rule.get("title"),
                "phase": rule.get("phase", "both"),
                "recommendations": rule.get("recommendations", []),
                "pay_items": rule.get("pay_items", []),
                "source": rule.get("source"),
                "explanation_template": rule.get("explanation_template"),
            }
        )
    return results
