"""
test_validation_engine.py
-------------------------
Comprehensive unit tests for the Validation Engine.
Tests all failure modes using small synthetic in-memory fixtures:
- Schema failures & missing columns
- Unexpected/undocumented columns
- Duplicate logical keys
- Invalid chapter codes
- Unexpected state identifiers
- Negative movement values
- Non-numeric values & infinite values
- Completeness failures
- Configurable tolerance behavior
- PASS / WARNING / FAIL classification
"""

import pytest
import pandas as pd
import numpy as np

from src.reconciliation.config import ReconciliationConfig
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationStatus, ValidationSeverity
from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer


@pytest.fixture
def real_dataset():
    """Loads actual real dataset."""
    loader = EwayBillSourceLoader("data/Road_EwayBill_2023_24.xlsx")
    raw = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw["tables"])
    norm = normalizer.normalize_all()
    return raw, norm


@pytest.fixture
def engine():
    return ValidationEngine()


# -----------------------------------------------------------------------------
# 1. Real Data Engine Execution Test
# -----------------------------------------------------------------------------

def test_validation_engine_runs_on_real_dataset(engine, real_dataset):
    """Verifies that all checks execute and pass on real production data."""
    raw_data, norm_tables = real_dataset
    results = engine.run_all_validations(raw_data, norm_tables, run_id="test-run-real")
    assert len(results) >= 30

    failures = [r for r in results if r.status == ValidationStatus.FAIL.value]
    assert len(failures) == 0, f"Found unexpected failures on real dataset: {[(f.check_id, f.message) for f in failures]}"


# -----------------------------------------------------------------------------
# 2. Schema Failure Tests (Synthetic)
# -----------------------------------------------------------------------------

def test_schema_missing_column(engine, real_dataset):
    """Test SCH-02: Missing required columns fails validation."""
    raw_data, norm_tables = real_dataset
    # Create synthetic copy missing 'origin_state'
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["state_movement"] = corrupted_tables["state_movement"].drop(columns=["origin_state"])

    results = engine.validate_schema(raw_data, corrupted_tables)
    failed = [r for r in results if r.check_id == "SCH-02-state_movement"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value
    assert failed[0].severity == ValidationSeverity.CRITICAL.value


def test_schema_unexpected_column(engine, real_dataset):
    """Test SCH-03: Undocumented business column produces a WARNING."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["chapter_movement"]["undocumented_tax_bracket"] = "18%"

    results = engine.validate_schema(raw_data, corrupted_tables)
    warn = [r for r in results if r.check_id == "SCH-03-chapter_movement"]
    assert len(warn) == 1
    assert warn[0].status == ValidationStatus.WARNING.value
    assert "undocumented_tax_bracket" in warn[0].message


# -----------------------------------------------------------------------------
# 3. Completeness Failure Tests (Synthetic)
# -----------------------------------------------------------------------------

def test_completeness_missing_records(engine, real_dataset):
    """Test CMP-02: Dropping rows from chapter_movement fails completeness."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Drop 5 rows
    corrupted_tables["chapter_movement"] = corrupted_tables["chapter_movement"].iloc[:-5]

    results = engine.validate_completeness(raw_data, corrupted_tables)
    failed = [r for r in results if r.check_id == "CMP-02"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value
    assert failed[0].difference == 5.0


def test_completeness_missing_chapter_code(engine, real_dataset):
    """Test CMP-06: Missing a required HS chapter code fails completeness."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Filter out Chapter 10
    corrupted_tables["chapter_movement"] = corrupted_tables["chapter_movement"][
        corrupted_tables["chapter_movement"]["chapter_code"] != "10"
    ]

    results = engine.validate_completeness(raw_data, corrupted_tables)
    failed = [r for r in results if r.check_id == "CMP-06"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value


def test_completeness_cmp_06_governance_documentation(engine, real_dataset):
    """Test CMP-06: Verifies governance message and that absence of 01-09 is not attributed to statutory scope."""
    raw_data, norm_tables = real_dataset
    results = engine.validate_completeness(raw_data, norm_tables)
    cmp06 = [r for r in results if r.check_id == "CMP-06"]
    assert len(cmp06) == 1
    assert cmp06[0].status == ValidationStatus.PASS.value
    expected_doc = (
        "The source dataset contains HS Chapters 10–99. Chapters 01–09 are absent "
        "from the source. The reason for their absence is not documented in the "
        "workbook and is not asserted by this validation engine."
    )
    assert cmp06[0].message == expected_doc
    assert "statutorily" not in cmp06[0].message


# -----------------------------------------------------------------------------
# 4. Uniqueness Failure Tests (Synthetic)
# -----------------------------------------------------------------------------

def test_uniqueness_duplicate_keys(engine, real_dataset):
    """Test UNQ-01: Duplicate natural keys fails uniqueness validation."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Duplicate first row
    first_row = corrupted_tables["state_movement"].iloc[[0]]
    corrupted_tables["state_movement"] = pd.concat([first_row, corrupted_tables["state_movement"]], ignore_index=True)

    results = engine.validate_uniqueness(corrupted_tables)
    failed = [r for r in results if r.check_id == "UNQ-01"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value
    assert failed[0].affected_records == 2  # Both duplicate instances flagged


# -----------------------------------------------------------------------------
# 5. Domain Failure Tests (Synthetic)
# -----------------------------------------------------------------------------

def test_domain_unexpected_state(engine, real_dataset):
    """Test DOM-01: Foreign/unexpected state identifier fails domain check."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Inject unknown state
    corrupted_tables["state_movement"].loc[0, "origin_state"] = "CALIFORNIA"

    results = engine.validate_domain(corrupted_tables)
    failed = [r for r in results if r.check_id == "DOM-01-state_movement"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value
    assert "CALIFORNIA" in str(failed[0].observed)


def test_domain_source_spelling_mutation(engine, real_dataset):
    """Test DOM-02: Renaming 'CHATTISGARH' to 'CHHATTISGARH' fails spelling check."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Mutate source spelling
    corrupted_tables["state_movement"]["origin_state"] = corrupted_tables["state_movement"]["origin_state"].replace(
        {"CHATTISGARH": "CHHATTISGARH"}
    )

    results = engine.validate_domain(corrupted_tables)
    failed = [r for r in results if r.check_id == "DOM-02"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value


def test_domain_invalid_chapter_format(engine, real_dataset):
    """Test DOM-03: Invalid chapter code format (e.g. non-digits or length != 2) fails."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["chapter_movement"].loc[0, "chapter_code"] = "XYZ"

    results = engine.validate_domain(corrupted_tables)
    failed = [r for r in results if r.check_id == "DOM-03-chapter_movement"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value


# -----------------------------------------------------------------------------
# 6. Numeric Failure Tests (Synthetic)
# -----------------------------------------------------------------------------

def test_numeric_negative_values(engine, real_dataset):
    """Test NUM-02: Negative movement values fails numeric validation."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Inject negative value
    corrupted_tables["chapter_movement"].loc[0, "movement_value_inr_crore"] = -150.0

    results = engine.validate_numeric(corrupted_tables)
    failed = [r for r in results if r.check_id == "NUM-02-chapter_movement"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value
    assert failed[0].affected_records == 1


def test_numeric_non_numeric_values(engine, real_dataset):
    """Test NUM-01: String in movement value fails numeric validation."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["state_chapter_outward"]["movement_value_inr_crore"] = corrupted_tables["state_chapter_outward"]["movement_value_inr_crore"].astype(object)
    corrupted_tables["state_chapter_outward"].loc[0, "movement_value_inr_crore"] = "CORRUPTED_STRING"

    results = engine.validate_numeric(corrupted_tables)
    failed = [r for r in results if r.check_id == "NUM-01-state_chapter_outward"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value


def test_numeric_infinite_values(engine, real_dataset):
    """Test NUM-03: np.inf fails infinite value detection."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["state_chapter_inward"].loc[0, "movement_value_inr_crore"] = np.inf

    results = engine.validate_numeric(corrupted_tables)
    failed = [r for r in results if r.check_id == "NUM-03-state_chapter_inward"]
    assert len(failed) == 1
    assert failed[0].status == ValidationStatus.FAIL.value


# -----------------------------------------------------------------------------
# 7. Configurable Tolerance Behavior Test
# -----------------------------------------------------------------------------

def test_tolerance_behavior():
    """Test configurable tolerance: small discrepancy passes with high tolerance, fails with strict."""
    # Strict tolerance: 1e-15
    strict_config = ReconciliationConfig(absolute_tolerance=1e-15)
    strict_engine = ValidationEngine(config=strict_config)

    # Moderate tolerance: 1.0
    loose_config = ReconciliationConfig(absolute_tolerance=1.0)
    loose_engine = ValidationEngine(config=loose_config)

    # Synthetic raw data with small rounding error of 0.005 in Table II
    loader = EwayBillSourceLoader("data/Road_EwayBill_2023_24.xlsx")
    raw_data = loader.load_raw_workbook()
    # Introduce small difference of 0.005 in reported total
    raw_data["metadata"]["worksheets"]["Tab II_Chap_Revised_Road"]["reported_total_row_93"] += 0.005

    # Loose engine should PASS
    res_loose = loose_engine.validate_source_totals(raw_data)
    rec_v01_loose = [r for r in res_loose if r.check_id == "REC-V01"][0]
    assert rec_v01_loose.status == ValidationStatus.PASS.value

    # Strict engine should FAIL
    res_strict = strict_engine.validate_source_totals(raw_data)
    rec_v01_strict = [r for r in res_strict if r.check_id == "REC-V01"][0]
    assert rec_v01_strict.status == ValidationStatus.FAIL.value
