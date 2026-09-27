"""
test_validation_rules.py
------------------------
Unit tests for intra-table mathematical verification checks (REC-V01 to REC-V08).
"""

import pytest

from src.ingestion.loader import EwayBillSourceLoader
from src.validation.rules import IntraTableValidator
from src.reconciliation.config import ReconciliationConfig


@pytest.fixture(scope="module")
def raw_data():
    loader = EwayBillSourceLoader(file_path="data/Road_EwayBill_2023_24.xlsx")
    return loader.load_raw_workbook()


@pytest.fixture(scope="module")
def validator(raw_data):
    return IntraTableValidator(raw_data)


def test_rec_v01_table_ii_row_sum(validator):
    """REC-V01: Table II Chapter Row Summation vs. Row 93 Total."""
    res = validator.check_rec_v01()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance
    assert res.expected_value == 20319786.98011017


def test_rec_v02_table_iii_state_outward_sum(validator):
    """REC-V02: Table III State Outward Column Summation vs. Row 93."""
    res = validator.check_rec_v02()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance


def test_rec_v03_table_iv_state_inward_sum(validator):
    """REC-V03: Table IV State Inward Column Summation vs. Row 93."""
    res = validator.check_rec_v03()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance


def test_rec_v04_table_iv_chapter_inward_sum(validator):
    """REC-V04: Table IV Chapter Inward Row Summation vs. Column AK."""
    res = validator.check_rec_v04()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance


def test_rec_v05_table_iv_grand_total_cross_foot(validator):
    """REC-V05: Table IV Dual-Dimension Grand Total Cross-Foot into AK93."""
    res = validator.check_rec_v05()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance
    assert abs(res.expected_value - 10429324.40404665) <= 1e-4


def test_rec_v06_table_v_state_internal_sum(validator):
    """REC-V06: Table V State Internal Column Summation vs. Row 93."""
    res = validator.check_rec_v06()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance


def test_rec_v07_table_v_chapter_internal_sum(validator):
    """REC-V07: Table V Chapter Internal Row Summation vs. Column AK."""
    res = validator.check_rec_v07()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance


def test_rec_v08_table_v_grand_total_cross_foot(validator):
    """REC-V08: Table V Dual-Dimension Grand Total Cross-Foot into AK93."""
    res = validator.check_rec_v08()
    assert res.status == "PASS"
    assert res.difference <= res.tolerance
    assert abs(res.expected_value - 9890462.576063517) <= 1e-4
