"""Tests for BidTabs scanning and contract selection."""

from pathlib import Path

import pandas as pd

from ec_train.bidtabs import BidTabContract, PAY_ITEM_TARGET, scan_bidtabs, select_contracts


def test_scan_bidtabs_filters_pay_item(tmp_path: Path):
    data = {
        "ContractNumber": ["R-12345", "R-12345", "R-99999"],
        "ItemNumber": [PAY_ITEM_TARGET, "OTHER", PAY_ITEM_TARGET],
        "Description": ["205-12616 Erosion Control", "Other", "205-12616"],
        "Quantity": [10, 5, 20],
        "LettingDate": ["2024-02-01", "2024-02-01", "2023-12-01"],
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "bidtabs.csv"
    df.to_csv(csv_path, index=False)

    contracts = scan_bidtabs(csv_path)
    assert {c.contract for c in contracts} == {"R-12345", "R-99999"}
    qty_lookup = {c.contract: c.bidtabs_qty for c in contracts}
    assert qty_lookup["R-12345"] == 15
    assert qty_lookup["R-99999"] == 20


def test_select_contracts_skips_seen(tmp_path: Path):
    candidates = [
        BidTabContract(contract="A"),
        BidTabContract(contract="B"),
        BidTabContract(contract="C"),
    ]
    selected = select_contracts(candidates, count=2, seen_contracts={"A"})
    assert len(selected) == 2
    assert all(c.contract != "A" for c in selected)
