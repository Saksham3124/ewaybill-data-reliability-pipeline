"""
test_normalization.py
---------------------
Unit tests for data normalization, schema conformity, duplicate detection,
data types, and row count verification across the 5 target normalized tables.
"""

import pytest
import pandas as pd
import numpy as np

from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer


@pytest.fixture(scope="module")
def normalized_tables():
    loader = EwayBillSourceLoader(file_path="data/Road_EwayBill_2023_24.xlsx")
    raw_data = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw_data["tables"])
    return normalizer.normalize_all()


def test_exact_normalized_row_counts(normalized_tables):
    """Test 1: Verify exact normalized row counts across all 5 tables."""
    # 1. state_movement: 33 * 33 = 1089
    df_sm = normalized_tables["state_movement"]
    assert len(df_sm) == 1089, f"Expected 1089 rows in state_movement, got {len(df_sm)}"

    # 2. chapter_movement: 90
    df_cm = normalized_tables["chapter_movement"]
    assert len(df_cm) == 90, f"Expected 90 rows in chapter_movement, got {len(df_cm)}"

    # 3. state_chapter_outward: 90 * 33 = 2970
    df_sco = normalized_tables["state_chapter_outward"]
    assert len(df_sco) == 2970, f"Expected 2970 rows in state_chapter_outward, got {len(df_sco)}"

    # 4. state_chapter_inward: 90 * 33 = 2970
    df_sci = normalized_tables["state_chapter_inward"]
    assert len(df_sci) == 2970, f"Expected 2970 rows in state_chapter_inward, got {len(df_sci)}"

    # 5. state_chapter_internal: 90 * 33 = 2970
    df_scint = normalized_tables["state_chapter_internal"]
    assert len(df_scint) == 2970, f"Expected 2970 rows in state_chapter_internal, got {len(df_scint)}"


def test_exact_field_names(normalized_tables):
    """Test 2: Verify strictly requested field names without undocumented additions."""
    # state_movement: origin_state, destination_state, movement_value_inr_crore
    assert list(normalized_tables["state_movement"].columns) == [
        "origin_state", "destination_state", "movement_value_inr_crore"
    ]

    # chapter_movement: chapter_code, chapter_description, movement_value_inr_crore
    assert list(normalized_tables["chapter_movement"].columns) == [
        "chapter_code", "chapter_description", "movement_value_inr_crore"
    ]

    # state_chapter_outward: chapter_code, chapter_description, state, movement_value_inr_crore
    assert list(normalized_tables["state_chapter_outward"].columns) == [
        "chapter_code", "chapter_description", "state", "movement_value_inr_crore"
    ]

    # state_chapter_inward: chapter_code, chapter_description, state, movement_value_inr_crore
    assert list(normalized_tables["state_chapter_inward"].columns) == [
        "chapter_code", "chapter_description", "state", "movement_value_inr_crore"
    ]

    # state_chapter_internal: chapter_code, chapter_description, state, movement_value_inr_crore
    assert list(normalized_tables["state_chapter_internal"].columns) == [
        "chapter_code", "chapter_description", "state", "movement_value_inr_crore"
    ]


def test_state_normalization(normalized_tables):
    """Test 3: Verify 33 distinct, trimmed, uppercase states across all state-bearing tables."""
    df_sm = normalized_tables["state_movement"]
    origins = set(df_sm["origin_state"])
    destinations = set(df_sm["destination_state"])
    assert len(origins) == 33
    assert len(destinations) == 33
    assert origins == destinations

    # Verify states in chapter-by-state tables
    for tbl_name in ("state_chapter_outward", "state_chapter_inward", "state_chapter_internal"):
        df = normalized_tables[tbl_name]
        states_in_tbl = set(df["state"])
        assert len(states_in_tbl) == 33
        assert states_in_tbl == origins
        assert "TOTAL" not in states_in_tbl, f"'TOTAL' aggregate column must not be present as state in {tbl_name}"


def test_chapter_code_normalization(normalized_tables):
    """Test 4: Verify 90 distinct 2-digit chapter codes ('10' through '99')."""
    expected_codes = set(str(i) for i in range(10, 100))

    for tbl_name in ("chapter_movement", "state_chapter_outward", "state_chapter_inward", "state_chapter_internal"):
        df = normalized_tables[tbl_name]
        codes_in_tbl = set(df["chapter_code"])
        assert len(codes_in_tbl) == 90
        assert codes_in_tbl == expected_codes
        # Verify string data type
        assert all(isinstance(c, str) for c in df["chapter_code"])


def test_duplicate_detection(normalized_tables):
    """Test 5: Verify zero duplicates on logical / natural composite keys."""
    # 1. state_movement: (origin_state, destination_state)
    df_sm = normalized_tables["state_movement"]
    dup_sm = df_sm.duplicated(subset=["origin_state", "destination_state"]).sum()
    assert dup_sm == 0, f"Found {dup_sm} duplicate pairs in state_movement"

    # 2. chapter_movement: (chapter_code)
    df_cm = normalized_tables["chapter_movement"]
    dup_cm = df_cm.duplicated(subset=["chapter_code"]).sum()
    assert dup_cm == 0, f"Found {dup_cm} duplicate chapter codes in chapter_movement"

    # 3. state_chapter_outward: (chapter_code, state)
    df_sco = normalized_tables["state_chapter_outward"]
    dup_sco = df_sco.duplicated(subset=["chapter_code", "state"]).sum()
    assert dup_sco == 0, f"Found {dup_sco} duplicate pairs in state_chapter_outward"

    # 4. state_chapter_inward: (chapter_code, state)
    df_sci = normalized_tables["state_chapter_inward"]
    dup_sci = df_sci.duplicated(subset=["chapter_code", "state"]).sum()
    assert dup_sci == 0, f"Found {dup_sci} duplicate pairs in state_chapter_inward"

    # 5. state_chapter_internal: (chapter_code, state)
    df_scint = normalized_tables["state_chapter_internal"]
    dup_scint = df_scint.duplicated(subset=["chapter_code", "state"]).sum()
    assert dup_scint == 0, f"Found {dup_scint} duplicate pairs in state_chapter_internal"


def test_numeric_type_and_null_preservation(normalized_tables):
    """Test 6: Verify movement values are float or None, and null counts match source."""
    # state_movement: 5 nulls
    df_sm = normalized_tables["state_movement"]
    assert df_sm["movement_value_inr_crore"].isna().sum() == 5
    non_null_sm = df_sm["movement_value_inr_crore"].dropna()
    assert all(isinstance(x, (float, int, np.floating)) for x in non_null_sm)

    # chapter_movement: 0 nulls
    df_cm = normalized_tables["chapter_movement"]
    assert df_cm["movement_value_inr_crore"].isna().sum() == 0

    # state_chapter_outward: 108 nulls
    df_sco = normalized_tables["state_chapter_outward"]
    assert df_sco["movement_value_inr_crore"].isna().sum() == 108

    # state_chapter_inward: 27 nulls
    df_sci = normalized_tables["state_chapter_inward"]
    assert df_sci["movement_value_inr_crore"].isna().sum() == 27

    # state_chapter_internal: 164 nulls
    df_scint = normalized_tables["state_chapter_internal"]
    assert df_scint["movement_value_inr_crore"].isna().sum() == 164
