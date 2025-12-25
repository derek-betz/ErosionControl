"""BidTabs ingestion and filtering utilities."""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PAY_ITEM_TARGET = "205-12616"


@dataclass(slots=True)
class BidTabContract:
    """Minimal representation of a contract from BidTabs."""

    contract: str
    letting_date: str | None = None
    district: str | None = None
    route: str | None = None
    bidtabs_qty: float | None = None


def _load_bidtabs(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def scan_bidtabs(path: Path, pay_item: str = PAY_ITEM_TARGET) -> list[BidTabContract]:
    """Scan a BidTabs export and return contracts containing the pay item."""
    df = _load_bidtabs(path)
    columns_lower = {col.lower(): col for col in df.columns}
    contract_col = (
        columns_lower.get("contract")
        or columns_lower.get("contractnumber")
        or next((col for col in df.columns if "contract" in col.lower()), None)
    )
    item_col = next((col for col in df.columns if "item" in col.lower()), None)
    desc_col = next((col for col in df.columns if "description" in col.lower()), None)
    qty_col = next((col for col in df.columns if "quantity" in col.lower()), None)
    letting_col = next((col for col in df.columns if "letting" in col.lower()), None)
    district_col = next((col for col in df.columns if "district" in col.lower()), None)
    route_col = next((col for col in df.columns if "route" in col.lower()), None)

    if contract_col is None or item_col is None:
        raise ValueError("BidTabs file must include contract and item columns.")

    df[item_col] = df[item_col].astype(str)
    matches = df[df[item_col].str.contains(pay_item, case=False, na=False)]
    if desc_col:
        matches = matches[
            matches[desc_col].fillna("").str.contains(pay_item.replace("-", " "), case=False)
            | matches[item_col].str.contains(pay_item, case=False)
        ]

    grouped = matches.groupby(df[contract_col].astype(str))
    contracts: list[BidTabContract] = []
    for contract_num, group in grouped:
        qty = float(group[qty_col].sum()) if qty_col else None
        contract = BidTabContract(
            contract=contract_num,
            letting_date=_first_non_null(group, letting_col),
            district=_first_non_null(group, district_col),
            route=_first_non_null(group, route_col),
            bidtabs_qty=qty,
        )
        contracts.append(contract)
    contracts.sort(key=lambda c: c.letting_date or "", reverse=True)
    return contracts


def _first_non_null(df: pd.DataFrame, col: str | None) -> str | None:
    if col is None or col not in df.columns:
        return None
    series = df[col].dropna()
    if series.empty:
        return None
    return str(series.iloc[0])


def select_contracts(
    candidates: Sequence[BidTabContract],
    count: int,
    seen_contracts: Iterable[str] | None = None,
    shuffle: bool = False,
) -> list[BidTabContract]:
    """Select contracts, skipping any already seen."""
    seen = {c.strip() for c in (seen_contracts or []) if c}
    pool = [c for c in candidates if c.contract not in seen]
    if shuffle:
        pool = pool.copy()
        random.shuffle(pool)
    return pool[:count]


__all__ = ["BidTabContract", "PAY_ITEM_TARGET", "scan_bidtabs", "select_contracts"]
