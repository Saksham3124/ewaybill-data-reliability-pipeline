"""
scripts/run_validation.py
-------------------------
Executable runner for Phase 4 Validation Engine.
Runs all validation checks on the real DGCI&S Road E-Way Bill dataset,
records check results into PostgreSQL validation_results table,
and generates docs/validation_report.md.
"""

import os
import sys
import uuid
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.ingestion.loader import EwayBillSourceLoader
from src.reconciliation.config import ReconciliationConfig
from src.transformation.normalizer import EwayBillNormalizer
from src.validation.engine import ValidationEngine
from src.validation.reporter import ValidationReporter


def main():
    source_file = "data/Road_EwayBill_2023_24.xlsx"
    if not os.path.exists(source_file):
        print(f"Error: Source workbook not found at {source_file}")
        sys.exit(1)

    print("==================================================")
    print("PHASE 4: VALIDATION ENGINE RUNNER")
    print("==================================================")

    # 1. Ingestion
    print(f"Loading source workbook: {source_file}...")
    loader = EwayBillSourceLoader(source_file)
    raw_data = loader.load_raw_workbook()
    print("Workbook successfully ingested into memory.")

    # 2. Normalization
    print("Normalizing sheets into relational structures...")
    normalizer = EwayBillNormalizer(raw_data["tables"])
    normalized_tables = normalizer.normalize_all()
    print("Normalization complete.")

    # 3. Database connection & Pipeline Run initialization
    print("\nConnecting to PostgreSQL database...")
    db_mgr = DatabaseManager()
    
    db_mgr.init_schema("sql/schema.sql")
    repo = EwayBillRepository(db_mgr)
    run_id = repo.start_pipeline_run(
        raw_data["metadata"]["source_filename"],
        raw_data["metadata"]["source_filepath"]
    )
    print(f"Started pipeline run in database: {run_id}")

    # 4. Validation
    print("Initializing ValidationEngine...")
    config = ReconciliationConfig(absolute_tolerance=0.01, relative_tolerance=1e-5)
    engine = ValidationEngine(config=config)
    print(f"Running all validation categories (Run ID: {run_id})...")
    results = engine.run_all_validations(raw_data, normalized_tables, run_id=run_id)

    total_checks = len(results)
    passed_checks = sum(1 for r in results if r.status == "PASS")
    warning_checks = sum(1 for r in results if r.status == "WARNING")
    failed_checks = sum(1 for r in results if r.status == "FAIL")

    print(f"\nExecution Summary:")
    print(f"  Total Checks Executed: {total_checks}")
    print(f"  Passed Checks:         {passed_checks}")
    print(f"  Warning Checks:        {warning_checks}")
    print(f"  Failed Checks:         {failed_checks}")

    # 5. Generate Validation Report
    report_path = "docs/validation_report.md"
    print(f"\nGenerating Markdown validation report at {report_path}...")
    ValidationReporter.generate_report(results, run_id=run_id, output_file=report_path)
    print("Report generation complete.")

    # 6. Persist to PostgreSQL
    print(f"Persisting {total_checks} validation results into table 'validation_results'...")
    inserted_count = repo.record_validation_results(run_id, results)
    print(f"Successfully recorded {inserted_count} rows in 'validation_results'.")

    # Complete pipeline run
    repo.complete_pipeline_run(run_id, {}, [r.to_dict() for r in results])

    # Query total count from validation_results table
    conn = db_mgr.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM validation_results;")
            total_val_rows = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM validation_results WHERE run_id = %s;", (run_id,))
            current_run_rows = cur.fetchone()[0]
            print(f"Total rows currently in 'validation_results' table: {total_val_rows} (Current run: {current_run_rows})")
    finally:
        conn.close()

    print("\nPhase 4 validation pipeline completed successfully.")


if __name__ == "__main__":
    main()
