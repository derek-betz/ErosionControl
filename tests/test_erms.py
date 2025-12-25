"""Tests for ERMS helper logic."""

from ec_train.erms import _contract_search_term


def test_contract_search_term_extracts_five_digits():
    assert _contract_search_term("R -44177-A") == "44177"
    assert _contract_search_term("R-12345-A") == "12345"


def test_contract_search_term_fallbacks():
    assert _contract_search_term("ABC123456") == "23456"
    assert _contract_search_term("R-987-A") == "987"
