"""Tests for BidTabs scanning and contract selection."""

from pathlib import Path

import pandas as pd

from ec_train.bidtabs import PAY_ITEM_TARGET, BidTabContract, scan_bidtabs, select_contracts


def test_scan_bidtabs_filters_pay_item(tmp_path: Path):
    data = {
        "ContractNumber": ["R-12345", "R-12345", "R-99999"],
        "ItemNumber": [PAY_ITEM_TARGET, PAY_ITEM_TARGET, PAY_ITEM_TARGET],
        "Description": ["205-12616 Erosion Control", "Other", "205-12616"],
        "Quantity": [10, 5, 20],
        "LettingDate": ["2024-02-01", "2024-02-01", "2023-12-01"],
        "Job Size": [2_500_000, 2_500_000, 12_000_000],
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "bidtabs.csv"
    df.to_csv(csv_path, index=False)

    contracts = scan_bidtabs(csv_path)
    assert {c.contract for c in contracts} == {"R-12345", "R-99999"}
    qty_lookup = {c.contract: c.bidtabs_qty for c in contracts}
    assert qty_lookup["R-12345"] == 15
    assert qty_lookup["R-99999"] == 20
    size_lookup = {c.contract: c.job_size for c in contracts}
    assert size_lookup["R-12345"] == 2_500_000
    assert size_lookup["R-99999"] == 12_000_000


def test_select_contracts_skips_seen(tmp_path: Path):
    candidates = [
        BidTabContract(contract="A"),
        BidTabContract(contract="B"),
        BidTabContract(contract="C"),
    ]
    selected = select_contracts(candidates, count=2, seen_contracts={"A"})
    assert len(selected) == 2
    assert all(c.contract != "A" for c in selected)


def test_select_contracts_filters_by_job_size():
    candidates = [
        BidTabContract(contract="A", job_size=1_000_000),
        BidTabContract(contract="B", job_size=5_000_000),
        BidTabContract(contract="C", job_size=None),
    ]
    selected = select_contracts(
        candidates,
        count=5,
        min_job_size=2_000_000,
        max_job_size=10_000_000,
    )
    assert [c.contract for c in selected] == ["B"]


def test_cloud_sample_has_minimum_contracts():
    sample_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "ec_train"
        / "data"
        / "bidtabs_cloud_sample.csv"
    )
    contracts = scan_bidtabs(sample_path)
    assert len(contracts) >= 10
    assert len({c.contract for c in contracts}) >= 10
