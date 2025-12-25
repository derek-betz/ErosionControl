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
    job_size: float | None = None


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
        or columns_lower.get("projectid")
        or columns_lower.get("project id")
        or next((col for col in df.columns if "contract" in col.lower()), None)
        or next((col for col in df.columns if "project" in col.lower() and "id" in col.lower()), None)
    )
    item_col = next((col for col in df.columns if "item" in col.lower()), None)
    desc_col = next((col for col in df.columns if "description" in col.lower()), None)
    qty_col = next((col for col in df.columns if "quantity" in col.lower()), None)
    letting_col = next((col for col in df.columns if "letting" in col.lower()), None)
    district_col = next((col for col in df.columns if "district" in col.lower()), None)
    route_col = next((col for col in df.columns if "route" in col.lower()), None)
    job_size_col = (
        columns_lower.get("job size")
        or columns_lower.get("jobsize")
        or columns_lower.get("contract amount")
        or columns_lower.get("total bid")
        or columns_lower.get("bid total")
        or columns_lower.get("total amount")
        or columns_lower.get("award amount")
        or next((col for col in df.columns if "job size" in col.lower()), None)
        or next(
            (col for col in df.columns if "contract" in col.lower() and "amount" in col.lower()),
            None,
        )
        or next((col for col in df.columns if "total" in col.lower() and "bid" in col.lower()), None)
    )

    if contract_col is None or item_col is None:
        raise ValueError("BidTabs file must include contract and item columns.")

    df[item_col] = df[item_col].astype(str)
    matches = df[df[item_col].str.contains(pay_item, case=False, na=False)]
    if desc_col:
        matches = matches[
            matches[desc_col].fillna("").str.contains(pay_item.replace("-", " "), case=False)
            | matches[item_col].str.contains(pay_item, case=False)
        ]

    grouped = matches.groupby(matches[contract_col].astype(str))
    contracts: list[BidTabContract] = []
    for contract_num, group in grouped:
        qty = float(group[qty_col].sum()) if qty_col else None
        job_size = _first_float(group, job_size_col)
        contract = BidTabContract(
            contract=contract_num,
            letting_date=_first_non_null(group, letting_col),
            district=_first_non_null(group, district_col),
            route=_first_non_null(group, route_col),
            bidtabs_qty=qty,
            job_size=job_size,
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


def _first_float(df: pd.DataFrame, col: str | None) -> float | None:
    if col is None or col not in df.columns:
        return None
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[0])


def select_contracts(
    candidates: Sequence[BidTabContract],
    count: int,
    seen_contracts: Iterable[str] | None = None,
    min_job_size: float | None = None,
    max_job_size: float | None = None,
    shuffle: bool = False,
) -> list[BidTabContract]:
    """Select contracts, skipping any already seen."""
    seen = {c.strip() for c in (seen_contracts or []) if c}
    pool = [c for c in candidates if c.contract not in seen and _in_job_size_range(c, min_job_size, max_job_size)]
    if shuffle:
        pool = pool.copy()
        random.shuffle(pool)
    return pool[:count]


def _in_job_size_range(
    contract: BidTabContract, min_job_size: float | None, max_job_size: float | None
) -> bool:
    if min_job_size is None and max_job_size is None:
        return True
    if contract.job_size is None:
        return False
    if min_job_size is not None and contract.job_size < min_job_size:
        return False
    if max_job_size is not None and contract.job_size > max_job_size:
        return False
    return True


__all__ = ["BidTabContract", "PAY_ITEM_TARGET", "scan_bidtabs", "select_contracts"]
