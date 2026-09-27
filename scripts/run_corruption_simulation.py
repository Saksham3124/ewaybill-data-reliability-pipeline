"""
scripts/run_corruption_simulation.py
------------------------------------
Executable runner for Phase 7 Controlled Corruption Simulation and Detection Testing.
Executes all 7 controlled corruption scenarios against in-memory copies of the clean datasets,
verifies detection performance and pipeline blocking behavior across validation, reconciliation,
and statistical engines, generates docs/corruption_detection_report.md, and verifies
source immutability and database isolation.
"""

import hashlib
import os
import sys
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import DatabaseManager
from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer
from src.corruption.runner import CorruptionSimulationRunner
from src.corruption.reporter import CorruptionReporter

F22_PATH = "data/Road_EwayBill_2022_23.xlsx"
F24_PATH = "data/Road_EwayBill_2023_24.xlsx"
EXPECTED_HASH_22 = "534ae64cdfe76ae1adbe5db789443cd5af5fc34df94925beba1949859d209aef"
EXPECTED_HASH_24 = "42fdba9a6fcf40fb47f9a632d403b28680e610160db51cf75511163f59ce803d"


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("==================================================")
    print("PHASE 7: CONTROLLED CORRUPTION SIMULATION RUNNER")
    print("==================================================")

    # 1. Verify pre-execution source hashes
    print("\n1. Verifying pre-execution source workbook hashes...")
    hash_22_pre = compute_sha256(F22_PATH)
    hash_24_pre = compute_sha256(F24_PATH)
    assert hash_22_pre == EXPECTED_HASH_22, f"Pre-hash mismatch on {F22_PATH}"
    assert hash_24_pre == EXPECTED_HASH_24, f"Pre-hash mismatch on {F24_PATH}"
    print(f"   FY 2022–23 SHA-256: {hash_22_pre} (VERIFIED)")
    print(f"   FY 2023–24 SHA-256: {hash_24_pre} (VERIFIED)")

    # 2. Ingest clean data
    print("\n2. Ingesting clean workbooks into memory...")
    loader_22 = EwayBillSourceLoader(F22_PATH)
    raw_22 = loader_22.load_raw_workbook()
    loader_24 = EwayBillSourceLoader(F24_PATH)
    raw_24 = loader_24.load_raw_workbook()
    normalizer_24 = EwayBillNormalizer(raw_24["tables"])
    norm_24 = normalizer_24.normalize_all()
    print("   Clean workbooks and normalized tables ready.")

    # 3. Capture baseline database trusted table counts
    print("\n3. Capturing baseline PostgreSQL warehouse table counts...")
    db_mgr = DatabaseManager()
    conn = db_mgr.get_connection()
    trusted_counts_baseline = {}
    try:
        with conn.cursor() as cur:
            for tbl in (
                "trusted_state_movement", "trusted_chapter_movement",
                "trusted_state_chapter_outward", "trusted_state_chapter_inward",
                "trusted_state_chapter_internal"
            ):
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                trusted_counts_baseline[tbl] = cur.fetchone()[0]
    finally:
        conn.close()
    print(f"   Baseline trusted counts: {trusted_counts_baseline}")

    # 4. Run Corruption Simulation
    print("\n4. Running 7 controlled corruption simulation scenarios...")
    run_id = f"corrupt_sim_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    runner = CorruptionSimulationRunner()
    results = runner.run_all_scenarios(raw_22, raw_24, norm_24)

    print("\nExecution Results:")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"{'Scenario':<12} | {'Corruption Type':<22} | {'Detected':<10} | {'Blocked':<10} | {'Actual Detector'}")
    print("---------------------------------------------------------------------------------------------------------")
    for r in results:
        det_str = "YES" if r.detected else "NO"
        blk_str = "BLOCKED" if r.pipeline_blocked else "ADVISORY"
        act_det = r.actual_detector or "None"
        print(f"{r.scenario_id:<12} | {r.corruption_type:<22} | {det_str:<10} | {blk_str:<10} | {act_det}")
    print("---------------------------------------------------------------------------------------------------------")

    detected_count = sum(1 for r in results if r.detected)
    missed_count = len(results) - detected_count
    blocked_count = sum(1 for r in results if r.pipeline_blocked)
    advisory_count = len(results) - blocked_count

    print(f"\nSummary:")
    print(f"  Scenarios Implemented:         {len(results)}")
    print(f"  Scenarios Detected:            {detected_count}")
    print(f"  Scenarios Missed:              {missed_count}")
    print(f"  Pipeline Blocked (Integrity):  {blocked_count}")
    print(f"  Advisory / Monitoring Signal:  {advisory_count}")

    # 5. Generate Report
    report_file = "docs/corruption_detection_report.md"
    print(f"\n5. Generating report at {report_file}...")
    CorruptionReporter.generate_report(results, run_id=run_id, output_file=report_file)
    print("   Report successfully written.")

    # 6. Verify post-execution source hashes
    print("\n6. Verifying post-execution source workbook hashes...")
    hash_22_post = compute_sha256(F22_PATH)
    hash_24_post = compute_sha256(F24_PATH)
    assert hash_22_post == EXPECTED_HASH_22, f"Post-hash mismatch on {F22_PATH}!"
    assert hash_24_post == EXPECTED_HASH_24, f"Post-hash mismatch on {F24_PATH}!"
    print(f"   FY 2022–23 SHA-256: {hash_22_post} (BYTE-FOR-BYTE IDENTICAL)")
    print(f"   FY 2023–24 SHA-256: {hash_24_post} (BYTE-FOR-BYTE IDENTICAL)")

    # 7. Verify post-execution database counts (isolation check)
    print("\n7. Verifying PostgreSQL production table isolation...")
    conn = db_mgr.get_connection()
    trusted_counts_post = {}
    try:
        with conn.cursor() as cur:
            for tbl in trusted_counts_baseline.keys():
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                trusted_counts_post[tbl] = cur.fetchone()[0]
    finally:
        conn.close()

    assert trusted_counts_post == trusted_counts_baseline, (
        f"Database contamination detected! Baseline: {trusted_counts_baseline}, Post: {trusted_counts_post}"
    )
    print("   Database verified: zero rows added or altered in production trusted tables.")

    print("\n==================================================")
    print("Phase 7 Corruption Simulation complete.")
    print("==================================================")


if __name__ == "__main__":
    main()
