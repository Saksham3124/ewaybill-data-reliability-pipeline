"""
test_ingestion.py
-----------------
Unit tests for source workbook discovery, sheet validation, row/column extraction,
and strict NULL preservation in the raw layer.
"""

import pytest
from pathlib import Path
import openpyxl

from src.ingestion.loader import EwayBillSourceLoader, MissingWorksheetError
from src.reconciliation.config import ReconciliationConfig


@pytest.fixture(scope="module")
def source_path():
    path = Path("data/Road_EwayBill_2023_24.xlsx")
    assert path.exists(), f"Source workbook must exist at: {path.resolve()}"
    return str(path)


@pytest.fixture(scope="module")
def loader(source_path):
    return EwayBillSourceLoader(file_path=source_path)


@pytest.fixture(scope="module")
def raw_data(loader):
    return loader.load_raw_workbook()


def test_workbook_discovery(loader, source_path):
    """Test 1: Verify workbook discovery and existence check."""
    sheets = loader.discover_and_validate()
    assert len(sheets) == 5
    assert "Tab I_Stat_to_Stat_Revised_Road" in sheets


def test_expected_worksheet_validation(source_path):
    """Test 2: Verify validation fails if expected worksheets are missing."""
    custom_config = ReconciliationConfig(expected_worksheets=("Non_Existent_Sheet_XYZ",))
    invalid_loader = EwayBillSourceLoader(file_path=source_path, config=custom_config)
    with pytest.raises(MissingWorksheetError):
        invalid_loader.discover_and_validate()


def test_row_column_extraction(raw_data):
    """Test 3: Verify exact data row and column counts per extracted table."""
    tables = raw_data["tables"]
    meta = raw_data["metadata"]["worksheets"]

    # Table I: 33 states x 33 states (+1 for to_state col)
    df_s1 = tables["raw_state_to_state"]
    assert len(df_s1) == 33
    assert len(df_s1.columns) == 34
    assert meta["Tab I_Stat_to_Stat_Revised_Road"]["data_start_row"] == 4
    assert meta["Tab I_Stat_to_Stat_Revised_Road"]["data_end_row"] == 36

    # Table II: 90 chapters, 3 columns
    df_s2 = tables["raw_chapter_summary"]
    assert len(df_s2) == 90
    assert len(df_s2.columns) == 3
    assert meta["Tab II_Chap_Revised_Road"]["data_start_row"] == 3
    assert meta["Tab II_Chap_Revised_Road"]["data_end_row"] == 92

    # Table III: 90 chapters, 33 states (+2 for code, desc)
    df_s3 = tables["raw_chapter_outward"]
    assert len(df_s3) == 90
    assert len(df_s3.columns) == 35

    # Table IV: 90 chapters, 33 states + TOTAL (+2 for code, desc)
    df_s4 = tables["raw_chapter_inward"]
    assert len(df_s4) == 90
    assert len(df_s4.columns) == 36
    assert "TOTAL" in df_s4.columns

    # Table V: 90 chapters, 33 states + TOTAL (+2 for code, desc)
    df_s5 = tables["raw_chapter_internal"]
    assert len(df_s5) == 90
    assert len(df_s5.columns) == 36
    assert "TOTAL" in df_s5.columns


def test_null_preservation(raw_data):
    """Test 4: Verify source blanks/NULLs are preserved and NOT converted into zero."""
    tables = raw_data["tables"]

    # Table I: exactly 5 nulls in data matrix
    df_s1 = tables["raw_state_to_state"]
    null_s1 = df_s1.drop(columns=["to_state"]).isna().sum().sum()
    assert null_s1 == 5, f"Expected exactly 5 null cells in Table I, found {null_s1}"

    # Verify specific known null cell in Table I: Goa -> Manipur (destination Goa, origin Manipur)
    goa_row = df_s1[df_s1["to_state"] == "GOA"]
    assert len(goa_row) == 1
    assert goa_row["MANIPUR"].isna().values[0]
    assert goa_row["MANIPUR"].values[0] is not 0.0

    # Table III: exactly 108 nulls
    df_s3 = tables["raw_chapter_outward"]
    null_s3 = df_s3.drop(columns=["chapter_code", "chapter_description"]).isna().sum().sum()
    assert null_s3 == 108, f"Expected 108 null cells in Table III, found {null_s3}"

    # Table IV: exactly 27 nulls in state columns
    df_s4 = tables["raw_chapter_inward"]
    null_s4 = df_s4.drop(columns=["chapter_code", "chapter_description", "TOTAL"]).isna().sum().sum()
    assert null_s4 == 27, f"Expected 27 null cells in Table IV, found {null_s4}"

    # Table V: exactly 164 nulls in state columns
    df_s5 = tables["raw_chapter_internal"]
    null_s5 = df_s5.drop(columns=["chapter_code", "chapter_description", "TOTAL"]).isna().sum().sum()
    assert null_s5 == 164, f"Expected 164 null cells in Table V, found {null_s5}"


def test_metadata_completeness(raw_data):
    """Test 5: Verify ingestion metadata contains all required audit fields."""
    meta = raw_data["metadata"]
    assert meta["source_filename"] == "Road_EwayBill_2023_24.xlsx"
    assert "ingestion_timestamp" in meta
    assert len(meta["worksheets"]) == 5

    for ws_name in ("Tab I_Stat_to_Stat_Revised_Road", "Tab II_Chap_Revised_Road",
                    "Tab III_Outward_Revised_Road", "Tab IV_Inward_Revised_Road",
                    "Tab V_Internal_Revised_Road"):
        ws_meta = meta["worksheets"][ws_name]
        assert ws_meta["worksheet_name"] == ws_name
        assert ws_meta["row_count"] in (33, 90)
        assert ws_meta["column_count"] >= 3
