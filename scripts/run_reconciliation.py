"""
scripts/run_reconciliation.py
-----------------------------
Executable runner for Phase 5 Cross-Table Reconciliation Engine.
Executes all 6 DATA-OBSERVED reconciliation audits against the real DGCI&S dataset,
persists 103 check results to PostgreSQL table 'reconciliation_results',
and generates docs/reconciliation_report.md.
"""

import os
import sys
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.ingestion.loader import EwayBillSourceLoader
from src.reconciliation.config import ReconciliationConfig
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.reporter import ReconciliationReporter
from src.transformation.normalizer import EwayBillNormalizer


def main():
    source_file = "data/Road_EwayBill_2023_24.xlsx"
    if not os.path.exists(source_file):
        print(f"Error: Source workbook not found at {source_file}")
        sys.exit(1)

    print("==================================================")
    print("PHASE 5: CROSS-TABLE RECONCILIATION RUNNER")
    print("==================================================")

    # 1. Ingest
    print(f"Loading source workbook: {source_file}...")
    loader = EwayBillSourceLoader(source_file)
    raw_data = loader.load_raw_workbook()
    print("Workbook successfully ingested into memory.")

    # 2. Normalize
    print("Normalizing sheets into relational structures...")
    normalizer = EwayBillNormalizer(raw_data["tables"])
    normalized_tables = normalizer.normalize_all()
    print("Normalization complete.")

    # 3. Database connection & Pipeline Run initialization
    print("\nConnecting to PostgreSQL database...")
    db_mgr = DatabaseManager(
        host="127.0.0.1",
        port=5433,
        dbname="ewaybill_dw",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "Saksham@3124")
    )
    db_mgr.init_schema("sql/schema.sql")
    repo = EwayBillRepository(db_mgr)

    run_id = repo.start_pipeline_run(
        raw_data["metadata"]["source_filename"],
        raw_data["metadata"]["source_filepath"]
    )
    print(f"Started pipeline run in database: {run_id}")

    # 4. Run Reconciliation Engine
    print("Initializing ReconciliationEngine...")
    config = ReconciliationConfig(absolute_tolerance=0.0001, relative_tolerance=1e-7)
    engine = ReconciliationEngine(config=config)
    print(f"Running all DATA-OBSERVED cross-table audits (Run ID: {run_id})...")
    results = engine.run_all_reconciliations(raw_data, normalized_tables, run_id=run_id)

    total_audits = len(results)
    passed_audits = sum(1 for r in results if r.status == "PASS")
    warning_audits = sum(1 for r in results if r.status == "WARNING")
    unresolved_audits = sum(1 for r in results if r.status == "UNRESOLVED")
    failed_audits = sum(1 for r in results if r.status == "FAIL")

    print(f"\nExecution Summary:")
    print(f"  Total Audits Executed:       {total_audits}")
    print(f"  Passed Audits:               {passed_audits}")
    print(f"  Warning Audits:              {warning_audits}")
    print(f"  Unresolved Audits:           {unresolved_audits}")
    print(f"  Failed Audits (Blocking):    {failed_audits}")

    # 5. Generate Markdown Report
    report_path = "docs/reconciliation_report.md"
    print(f"\nGenerating Markdown reconciliation report at {report_path}...")
    ReconciliationReporter.generate_report(results, run_id=run_id, output_file=report_path)
    print("Report generation complete.")

    # 6. Persist to PostgreSQL
    print(f"Persisting {total_audits} reconciliation results into table 'reconciliation_results'...")
    inserted_count = repo.record_reconciliation_results(run_id, results)
    print(f"Successfully recorded {inserted_count} rows in 'reconciliation_results'.")

    # Mark pipeline run complete
    repo.complete_pipeline_run(run_id, {}, [r.to_dict() for r in results])

    # Query counts from database
    conn = db_mgr.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM reconciliation_results;")
            total_rec_rows = cur.fetchone()[0]
            cur.execute("SELECT status, COUNT(*) FROM reconciliation_results WHERE run_id = %s GROUP BY status;", (run_id,))
            status_counts = dict(cur.fetchall())
            print(f"Total rows currently in 'reconciliation_results' table: {total_rec_rows}")
            print(f"Current run counts by status: {status_counts}")
    finally:
        conn.close()

    print("\nPhase 5 reconciliation audit completed successfully.")


if __name__ == "__main__":
    main()
