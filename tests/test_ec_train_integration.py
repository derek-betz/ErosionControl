"""Integration test stub for EC Train networked workflow."""

import pytest

from ec_train.config import Config
from ec_train.erms import ERMSFetcher


@pytest.mark.skip(reason="Networked ERMS access requires credentials; enable when available.")
def test_erms_search_stub(tmp_path):
    cfg = Config.from_env()
    fetcher = ERMSFetcher(
        base_url=cfg.erms_url,
        download_dir=tmp_path,
        cookies=cfg.cookies,
        cookie_jar=cfg.cookie_jar,
    )
    assert fetcher.base_url.startswith("http")
