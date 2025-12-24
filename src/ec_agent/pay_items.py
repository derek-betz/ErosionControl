from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class PayItem:
    pay_item_number: str
    description: str
    unit: str
    notes: str
    source_doc_id: str


def load_pay_item_mapping(path: str | Path) -> Dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def build_catalog(mapping: Dict[str, Any]) -> Dict[str, PayItem]:
    catalog = {}
    for item in mapping.get("catalog", []):
        catalog[item["pay_item_number"]] = PayItem(
            pay_item_number=item["pay_item_number"],
            description=item["description"],
            unit=item.get("unit", ""),
            notes=item.get("notes", ""),
            source_doc_id=item.get("source_doc_id", "UNKNOWN"),
        )
    return catalog


def pay_items_for_practices(practices: List[str], mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    catalog = build_catalog(mapping)
    results: List[Dict[str, Any]] = []
    practice_map: Dict[str, List[Dict[str, str]]] = mapping.get("practice_map", {})
    for practice in practices:
        items = practice_map.get(practice, [])
        for item_ref in items:
            number = item_ref["pay_item_number"]
            catalog_item = catalog.get(number)
            notes = item_ref.get("notes", "")
            if catalog_item:
                results.append(
                    {
                        "practice": practice,
                        "pay_item_number": catalog_item.pay_item_number,
                        "description": catalog_item.description,
                        "unit": catalog_item.unit,
                        "notes": f"{notes} {catalog_item.notes}".strip(),
                        "source_doc_id": catalog_item.source_doc_id,
                    }
                )
            else:
                results.append(
                    {
                        "practice": practice,
                        "pay_item_number": number,
                        "description": item_ref.get("description", "VERIFY PAY ITEM NUMBER"),
                        "unit": item_ref.get("unit", ""),
                        "notes": f"{notes} VERIFY PAY ITEM NUMBER".strip(),
                        "source_doc_id": item_ref.get("source_doc_id", "UNKNOWN"),
                    }
                )
    return results
