"""
scripts/run_statistical_analysis.py
-----------------------------------
Executable runner for Phase 6 Year-over-Year Statistical Analysis.
Compares FY 2022–23 (historical baseline) vs. FY 2023–24 (production comparison),
executes Kolmogorov-Smirnov tests, Population Stability Index calculations,
and YoY unit change audits, generates docs/statistical_analysis_report.md,
and persists results into PostgreSQL table 'statistical_results'.
"""

import os
import sys
from collections import Counter
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.ingestion.loader import EwayBillSourceLoader
from src.statistics.config import StatisticalConfig
from src.statistics.engine import StatisticalAnalysisEngine
from src.statistics.models import StatisticalStatus
from src.statistics.reporter import StatisticalReporter


def main():
    file_2022_23 = "data/Road_EwayBill_2022_23.xlsx"
    file_2023_24 = "data/Road_EwayBill_2023_24.xlsx"

    if not os.path.exists(file_2022_23):
        print(f"Error: Historical reference workbook not found at {file_2022_23}")
        sys.exit(1)
    if not os.path.exists(file_2023_24):
        print(f"Error: Comparison workbook not found at {file_2023_24}")
        sys.exit(1)

    print("==================================================")
    print("PHASE 6: YEAR-OVER-YEAR STATISTICAL ANALYSIS")
    print("==================================================")

    # 1. Ingest both workbooks
    print(f"\n1. Ingesting historical reference workbook: {file_2022_23}...")
    loader_22 = EwayBillSourceLoader(file_2022_23)
    raw_22 = loader_22.load_raw_workbook()
    print("   FY 2022–23 successfully loaded into memory.")

    print(f"2. Ingesting comparison workbook: {file_2023_24}...")
    loader_24 = EwayBillSourceLoader(file_2023_24)
    raw_24 = loader_24.load_raw_workbook()
    print("   FY 2023–24 successfully loaded into memory.")

    # 2. Database connection & Pipeline Run initialization
    print("\n3. Connecting to PostgreSQL database...")
    db_mgr = DatabaseManager()
    db_mgr.init_schema("sql/schema.sql")
    repo = EwayBillRepository(db_mgr)

    run_id = repo.start_pipeline_run(
        raw_24["metadata"]["source_filename"],
        raw_24["metadata"]["source_filepath"]
    )
    print(f"   Started pipeline run in database: {run_id}")

    # 3. Run Statistical Analysis Engine
    print("\n4. Running Year-over-Year Statistical Analysis Engine...")
    config = StatisticalConfig(
        alpha=0.05,
        psi_threshold_moderate=0.10,
        psi_threshold_significant=0.25,
        psi_epsilon=1e-4
    )
    engine = StatisticalAnalysisEngine(config=config)
    results = engine.run_all_statistical_analyses(raw_22, raw_24, run_id=run_id)

    total_comparisons = len(results)
    ks_tests = [r for r in results if r.test_method == "KS_TEST"]
    psi_tests = [r for r in results if r.test_method == "PSI"]
    yoy_metrics = [r for r in results if r.test_method == "YOY_CHANGE"]
    ot_obs = [r for r in results if r.test_method == "CROSS_YEAR_OBSERVATION"]

    status_counts = Counter(r.status for r in results)
    stat_diff_count = status_counts.get(StatisticalStatus.STATISTICALLY_DIFFERENT.value, 0)
    no_change_count = status_counts.get(StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value, 0)
    insufficient_count = status_counts.get(StatisticalStatus.INSUFFICIENT_DATA.value, 0)
    na_count = status_counts.get(StatisticalStatus.NOT_APPLICABLE.value, 0)

    print("\n   Execution Summary:")
    print(f"     Total Statistical Comparisons:       {total_comparisons}")
    print(f"     KS Two-Sample Tests:                 {len(ks_tests)}")
    print(f"     PSI Distribution Tests:              {len(psi_tests)}")
    print(f"     YoY Unit Change Metrics:             {len(yoy_metrics)}")
    print(f"     Cross-Year Audit Observations:       {len(ot_obs)}")
    print(f"     - No Material Statistical Change:    {no_change_count}")
    print(f"     - Statistically Different:           {stat_diff_count}")
    print(f"     - Insufficient Data:                 {insufficient_count}")
    print(f"     - Not Applicable:                    {na_count}")

    # 4. Generate Markdown Report
    report_path = "docs/statistical_analysis_report.md"
    print(f"\n5. Generating Markdown statistical report at {report_path}...")
    StatisticalReporter.generate_report(results, run_id=run_id, output_file=report_path)
    print("   Report generation complete.")

    # 5. Persist to PostgreSQL
    print(f"\n6. Persisting {total_comparisons} statistical results into table 'statistical_results'...")
    inserted_count = repo.record_statistical_results(run_id, results)
    print(f"   Successfully recorded {inserted_count} rows in 'statistical_results'.")

    # Complete pipeline run
    repo.complete_pipeline_run(run_id, {}, [r.to_dict() for r in results])

    # Query counts from database
    conn = db_mgr.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM statistical_results;")
            total_stat_rows = cur.fetchone()[0]
            cur.execute(
                "SELECT status, COUNT(*) FROM statistical_results WHERE run_id = %s GROUP BY status;",
                (run_id,)
            )
            run_status_counts = dict(cur.fetchall())
            print(f"   Total rows currently in 'statistical_results' table: {total_stat_rows}")
            print(f"   Current run counts by status: {run_status_counts}")
    finally:
        conn.close()

    print("\n==================================================")
    print("Phase 6 Year-over-Year Statistical Analysis complete.")
    print("==================================================")


if __name__ == "__main__":
    main()
