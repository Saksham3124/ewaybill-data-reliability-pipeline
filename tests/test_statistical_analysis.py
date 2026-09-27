"""
tests/test_statistical_analysis.py
----------------------------------
Comprehensive unit and integration tests for Phase 6 Year-over-Year Statistical Analysis.
Verifies:
1. Canonical state normalization mappings and raw source label preservation.
2. Comparable dimension extraction and exclusion of Table III Column AK.
3. YoY absolute and percentage change calculations with zero/null denominator protection.
4. Kolmogorov-Smirnov two-sample testing (identical samples, shifts, alpha, sample size threshold).
5. Population Stability Index (identical, shifts, zero-bin handling, epsilon smoothing, thresholds).
6. Insufficient data handling (sample size < 5).
7. OTHER TERRITORY cross-year observation (FY 2022-23 equivalence, FY 2023-24 divergence, non-mutation).
8. Full statistical engine execution on real annual snapshots.
9. Absence of PASS/FAIL labels (strict use of allowed StatisticalStatus values).
10. Database persistence into 'statistical_results' table in PostgreSQL.
11. Markdown report generation and compliance with required sections.
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.ingestion.loader import EwayBillSourceLoader
from src.statistics.config import StatisticalConfig, CANONICAL_STATE_MAP
from src.statistics.engine import StatisticalAnalysisEngine
from src.statistics.models import StatisticalResult, StatisticalStatus
from src.statistics.reporter import StatisticalReporter

FILE_2022_23 = "data/Road_EwayBill_2022_23.xlsx"
FILE_2023_24 = "data/Road_EwayBill_2023_24.xlsx"


@pytest.fixture(scope="module")
def real_datasets():
    """Ingests both annual workbooks into memory."""
    loader_22 = EwayBillSourceLoader(FILE_2022_23)
    raw_22 = loader_22.load_raw_workbook()

    loader_24 = EwayBillSourceLoader(FILE_2023_24)
    raw_24 = loader_24.load_raw_workbook()

    return raw_22, raw_24


@pytest.fixture
def engine():
    return StatisticalAnalysisEngine()


# -----------------------------------------------------------------------------
# 1. Canonical State Normalization & Raw Preservation
# -----------------------------------------------------------------------------

def test_canonical_state_mappings(engine):
    """Test documented canonical state mappings across annual snapshots."""
    assert engine.canonical_state("CHHATTISGARH") == "CHATTISGARH"
    assert engine.canonical_state("CHATTISGARH") == "CHATTISGARH"
    assert engine.canonical_state("JAMMU AND KASHMIR") == "JAMMU & KASHMIR"
    assert engine.canonical_state("JAMMU & KASHMIR") == "JAMMU & KASHMIR"
    assert engine.canonical_state("Other Territory") == "OTHER TERRITORY"
    assert engine.canonical_state("OTHER TERRITORY") == "OTHER TERRITORY"
    # Unmapped states remain untouched
    assert engine.canonical_state("MAHARASHTRA") == "MAHARASHTRA"
    assert engine.canonical_state("TAMIL NADU") == "TAMIL NADU"
    assert engine.canonical_state("") == ""


def test_raw_source_labels_preserved(real_datasets):
    """Test that raw ingested tables preserve original source spelling/casing before normalization."""
    raw_22, raw_24 = real_datasets

    # In 2022-23 Table V, column was 'Other Territory'
    raw_v_22_cols = raw_22["tables"]["raw_chapter_internal"].columns
    assert "Other Territory" in raw_v_22_cols
    assert "OTHER TERRITORY" not in raw_v_22_cols

    # In 2023-24 Table V, column is 'OTHER TERRITORY'
    raw_v_24_cols = raw_24["tables"]["raw_chapter_internal"].columns
    assert "OTHER TERRITORY" in raw_v_24_cols


# -----------------------------------------------------------------------------
# 2. Comparable Dimension Extraction & Table III Column AK Exclusion
# -----------------------------------------------------------------------------

def test_comparable_dimensions_extraction(engine, real_datasets):
    """Test that comparable dimensions have expected entity counts and Table III Col AK is excluded."""
    raw_22, raw_24 = real_datasets
    dims = engine.extract_comparable_dimensions(raw_22, raw_24)

    assert "state_outward" in dims
    assert "state_inward" in dims
    assert "state_internal" in dims
    assert "chapter_national" in dims
    assert "state_chapter_outward" in dims
    assert "state_chapter_inward" in dims
    assert "state_chapter_internal" in dims

    # Verify state dimensions have exactly 33 canonical jurisdictions
    assert len(dims["state_outward"]) == 33
    assert len(dims["state_inward"]) == 33
    assert len(dims["state_internal"]) == 33

    # Verify national chapter dimension has exactly 90 chapters (10 to 99)
    assert len(dims["chapter_national"]) == 90
    assert dims["chapter_national"]["chapter_code"].iloc[0] == "10"
    assert dims["chapter_national"]["chapter_code"].iloc[-1] == "99"

    # Verify state-chapter matrices have exactly 2,970 combinations (90 * 33)
    assert len(dims["state_chapter_outward"]) == 2970
    assert len(dims["state_chapter_inward"]) == 2970
    assert len(dims["state_chapter_internal"]) == 2970

    # Ensure Column AK ("VALUE (in INR Crore)") was NOT included as a state entity
    outward_states = set(dims["state_chapter_outward"]["state"].unique())
    assert "VALUE (in INR Crore)" not in outward_states
    assert "TOTAL" not in outward_states
    assert len(outward_states) == 33


# -----------------------------------------------------------------------------
# 3. YoY Metric Calculation & Zero-Denominator Protection
# -----------------------------------------------------------------------------

def test_yoy_metric_calculation_standard(engine):
    """Test standard absolute and percentage change calculations."""
    abs_chg, pct_chg, note = engine.calculate_yoy_metrics(100.0, 125.0)
    assert abs_chg == pytest.approx(25.0)
    assert pct_chg == pytest.approx(25.0)
    assert note == "CALCULATED"

    abs_chg2, pct_chg2, note2 = engine.calculate_yoy_metrics(200.0, 150.0)
    assert abs_chg2 == pytest.approx(-50.0)
    assert pct_chg2 == pytest.approx(-25.0)
    assert note2 == "CALCULATED"


def test_yoy_metric_zero_denominator_protection(engine):
    """Test that zero denominator returns None and does not manufacture synthetic infinity."""
    abs_chg, pct_chg, note = engine.calculate_yoy_metrics(0.0, 100.0)
    assert abs_chg == pytest.approx(100.0)
    assert pct_chg is None
    assert "ZERO_DENOMINATOR" in note


def test_yoy_metric_null_handling(engine):
    """Test that NULL values return None for both absolute and percentage change."""
    abs_chg, pct_chg, note = engine.calculate_yoy_metrics(None, 50.0)
    assert abs_chg is None
    assert pct_chg is None
    assert note == "NULL_VALUE_PRESENT"

    abs_chg2, pct_chg2, note2 = engine.calculate_yoy_metrics(50.0, None)
    assert abs_chg2 is None
    assert pct_chg2 is None
    assert note2 == "NULL_VALUE_PRESENT"


# -----------------------------------------------------------------------------
# 4. Kolmogorov-Smirnov Two-Sample Test
# -----------------------------------------------------------------------------

def test_ks_test_identical_samples(engine):
    """Test KS test on identical samples produces statistic=0 and p=1.0."""
    sample = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    res = engine.run_ks_test(sample, sample, "TEST_DIM", "TEST_METRIC", "run_test")

    assert res.test_method == "KS_TEST"
    assert res.statistic == pytest.approx(0.0, abs=1e-5)
    assert res.p_value == pytest.approx(1.0, abs=1e-5)
    assert res.status == StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value


def test_ks_test_shifted_samples(engine):
    """Test KS test detects significant shift between differing distributions."""
    np.random.seed(42)
    s1 = np.random.normal(100, 10, 100)
    s2 = np.random.normal(200, 10, 100)
    res = engine.run_ks_test(s1, s2, "TEST_DIM", "TEST_METRIC", "run_test", alpha=0.05)

    assert res.status == StatisticalStatus.STATISTICALLY_DIFFERENT.value
    assert res.p_value < 0.05
    assert "does NOT indicate data corruption or pipeline failure" in res.interpretation


def test_ks_test_configurable_alpha():
    """Test that alpha is configurable and respected."""
    cfg = StatisticalConfig(alpha=0.001)
    eng = StatisticalAnalysisEngine(config=cfg)
    assert eng.config.alpha == 0.001


# -----------------------------------------------------------------------------
# 5. Population Stability Index (PSI)
# -----------------------------------------------------------------------------

def test_psi_test_identical_samples(engine):
    """Test PSI on identical samples produces PSI near 0.0."""
    sample = np.linspace(10, 1000, 50)
    res = engine.run_psi_test(sample, sample, "TEST_DIM", "TEST_METRIC", "run_test")

    assert res.test_method == "PSI"
    assert res.psi_value == pytest.approx(0.0, abs=1e-3)
    assert res.status == StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value


def test_psi_test_shifted_samples(engine):
    """Test PSI detects significant distributional shift."""
    np.random.seed(42)
    s1 = np.random.exponential(scale=10.0, size=200)
    s2 = np.random.exponential(scale=100.0, size=200)
    res = engine.run_psi_test(s1, s2, "TEST_DIM", "TEST_METRIC", "run_test")

    assert res.psi_value > 0.25
    assert res.status == StatisticalStatus.STATISTICALLY_DIFFERENT.value
    assert "PROJECT CONFIGURATION / INTERPRETATION GUIDANCE" in res.interpretation


def test_psi_zero_count_bins_epsilon_smoothing(engine):
    """Test that zero-count bins do not raise divide-by-zero or nan/inf errors."""
    s1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    s2 = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    res = engine.run_psi_test(s1, s2, "TEST_DIM", "TEST_METRIC", "run_test")

    assert np.isfinite(res.psi_value)
    assert res.psi_value >= 0.0


# -----------------------------------------------------------------------------
# 6. Sample Size Threshold & Insufficient Data Handling
# -----------------------------------------------------------------------------

def test_insufficient_data_handling(engine):
    """Test that samples with N < min_sample_size return INSUFFICIENT_DATA."""
    s_small = np.array([10.0, 20.0])
    s_normal = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

    ks_res = engine.run_ks_test(s_small, s_normal, "TEST_DIM", "TEST_METRIC", "run_test")
    assert ks_res.status == StatisticalStatus.INSUFFICIENT_DATA.value
    assert "Insufficient sample size" in ks_res.interpretation

    psi_res = engine.run_psi_test(s_small, s_normal, "TEST_DIM", "TEST_METRIC", "run_test")
    assert psi_res.status == StatisticalStatus.INSUFFICIENT_DATA.value
    assert "Insufficient sample size" in psi_res.interpretation


# -----------------------------------------------------------------------------
# 7. OTHER TERRITORY Cross-Year Observation
# -----------------------------------------------------------------------------

def test_other_territory_cross_year_audit(engine, real_datasets):
    """Test OTHER TERRITORY cross-year observation: holds in 2022-23, diverges in 2023-24."""
    raw_22, raw_24 = real_datasets
    res = engine.audit_other_territory_cross_year(raw_22, raw_24, "run_ot_test")

    assert res.dimension == "CROSS_YEAR_AUDIT"
    assert res.metric == "OTHER_TERRITORY_DIAGONAL_INTERNAL_EQUIVALENCE"
    assert res.test_method == "CROSS_YEAR_OBSERVATION"
    assert res.statistic == pytest.approx(76614.933539, abs=1e-3)
    assert res.status == StatisticalStatus.STATISTICALLY_DIFFERENT.value

    # Interpretation must describe historical agreement and production divergence
    assert "observed in FY2022–23" in res.interpretation
    assert "diff = 0.00000000 Cr" in res.interpretation or "diff = 0." in res.interpretation
    assert "diff = ₹76,614.933539 Cr" in res.interpretation
    assert "cause is not asserted" in res.interpretation


# -----------------------------------------------------------------------------
# 8. Full Suite Execution & Status Vocabulary
# -----------------------------------------------------------------------------

def test_full_engine_execution_on_real_data(engine, real_datasets):
    """Test running full statistical analysis suite on real FY 2022-23 and FY 2023-24 datasets."""
    raw_22, raw_24 = real_datasets
    results = engine.run_all_statistical_analyses(raw_22, raw_24, run_id="test_full_stat_run")

    assert len(results) == 204  # 7 KS + 7 PSI + 33*3 state YoY + 90 chapter YoY + 1 OT audit

    # Verify strict status vocabulary: NO 'PASS' or 'FAIL'
    valid_statuses = {s.value for s in StatisticalStatus}
    for r in results:
        assert r.status in valid_statuses, f"Invalid status '{r.status}' found in result {r.metric}"
        assert r.status not in ("PASS", "FAIL"), f"Forbidden status '{r.status}' used!"


# -----------------------------------------------------------------------------
# 9. Markdown Report Generation
# -----------------------------------------------------------------------------

def test_statistical_report_generation(engine, real_datasets, tmp_path):
    """Test generating docs/statistical_analysis_report.md."""
    raw_22, raw_24 = real_datasets
    results = engine.run_all_statistical_analyses(raw_22, raw_24, run_id="report_test_run")

    report_file = tmp_path / "test_statistical_report.md"
    content = StatisticalReporter.generate_report(results, "report_test_run", str(report_file))

    assert report_file.exists()
    assert "# Year-over-Year Statistical Analysis Report" in content
    assert "EPISTEMIC BOUNDARY & DATA QUALITY NOTICE" in content
    assert "Kolmogorov-Smirnov (KS) Two-Sample Test Results" in content
    assert "Population Stability Index (PSI) Results" in content
    assert "OTHER TERRITORY Cross-Year Historical Observation" in content
    assert "Limitations & Analytical Disclaimers" in content


# -----------------------------------------------------------------------------
# 10. Database Persistence Integration
# -----------------------------------------------------------------------------

def test_database_persistence_integration(engine, real_datasets):
    """Test persisting statistical results into PostgreSQL statistical_results table."""
    db_mgr = DatabaseManager()
    try:
        conn = db_mgr.get_connection()
        conn.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL connection unavailable: {e}")

    db_mgr.init_schema("sql/schema.sql")
    repo = EwayBillRepository(db_mgr)
    raw_22, raw_24 = real_datasets

    run_id = repo.start_pipeline_run("test_stat_source_24", "test_path_24")
    results = engine.run_all_statistical_analyses(raw_22, raw_24, run_id=run_id)

    inserted = repo.record_statistical_results(run_id, results)
    assert inserted == len(results)

    # Verify query
    conn = db_mgr.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM statistical_results WHERE run_id = %s;", (run_id,))
            count = cur.fetchone()[0]
            assert count == len(results)

            cur.execute("""
                SELECT test_method, COUNT(*) 
                FROM statistical_results 
                WHERE run_id = %s 
                GROUP BY test_method;
            """, (run_id,))
            method_counts = dict(cur.fetchall())
            assert method_counts["KS_TEST"] == 7
            assert method_counts["PSI"] == 7
            assert method_counts["YOY_CHANGE"] == 189  # 99 + 90
            assert method_counts["CROSS_YEAR_OBSERVATION"] == 1
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM statistical_results WHERE run_id = %s;", (run_id,))
                cur.execute("DELETE FROM pipeline_runs WHERE run_id = %s;", (run_id,))
            conn.commit()
        except Exception:
            pass
        conn.close()
