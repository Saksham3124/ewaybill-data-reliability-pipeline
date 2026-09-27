"""
database/repository.py
----------------------
Database repository for loading raw extractions and trusted normalized tables
into PostgreSQL with full run-level audit tracking.
"""

from typing import Dict, Any, List
import pandas as pd
from psycopg2.extras import execute_values, Json


class EwayBillRepository:
    """Handles raw audit staging and trusted normalization insertion."""

    def __init__(self, db_manager):
        self.db = db_manager

    def start_pipeline_run(self, source_filename: str, source_filepath: str, run_id: str = None) -> str:
        """Initializes a new pipeline run record, optionally using an existing deterministic UUID."""
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                if run_id:
                    cur.execute("""
                        INSERT INTO pipeline_runs (run_id, source_filename, source_filepath, status)
                        VALUES (%s::uuid, %s, %s, 'STARTED')
                        ON CONFLICT (run_id) DO UPDATE SET status = 'STARTED', ingestion_timestamp = NOW()
                        RETURNING run_id::text;
                    """, (run_id, source_filename, source_filepath))
                else:
                    cur.execute("""
                        INSERT INTO pipeline_runs (source_filename, source_filepath, status)
                        VALUES (%s, %s, 'STARTED')
                        RETURNING run_id::text;
                    """, (source_filename, source_filepath))
                actual_run_id = cur.fetchone()[0]
            conn.commit()
            return actual_run_id
        finally:
            conn.close()

    def fail_pipeline_run(self, run_id: str, error_message: str) -> None:
        """Marks pipeline run as failed with diagnostic message."""
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = 'FAILED',
                        validation_summary = %s,
                        completed_at = NOW()
                    WHERE run_id = %s::uuid;
                """, (Json([{"error": error_message}]), run_id))
            conn.commit()
        finally:
            conn.close()

    def complete_pipeline_run(self, run_id: str, row_counts: Dict[str, int], validation_summary: List[Dict[str, Any]]) -> None:
        """Marks pipeline run as completed with metrics and validation outcomes."""
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = 'COMPLETED',
                        row_counts = %s,
                        validation_summary = %s,
                        completed_at = NOW()
                    WHERE run_id = %s::uuid;
                """, (Json(row_counts), Json(validation_summary), run_id))
            conn.commit()
        finally:
            conn.close()

    def stage_raw_data(self, run_id: str, raw_data: Dict[str, Any]) -> Dict[str, int]:
        """Stages exact raw extractions and metadata into raw_* tables."""
        tables = raw_data["tables"]
        metadata = raw_data["metadata"]
        staged_counts = {}

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. raw_worksheet_metadata
                meta_records = []
                for ws_name, m in metadata["worksheets"].items():
                    meta_records.append((
                        run_id,
                        ws_name,
                        m.get("title"),
                        m.get("data_start_row"),
                        m.get("data_end_row"),
                        m.get("row_count"),
                        m.get("column_count"),
                        m.get("null_cells_count", 0),
                        m.get("reported_total_row_93") or m.get("reported_grand_total_cell_ak93"),
                        Json(m.get("reported_state_totals_row_93")) if m.get("reported_state_totals_row_93") else None
                    ))
                execute_values(cur, """
                    INSERT INTO raw_worksheet_metadata (
                        run_id, worksheet_name, title_text, data_start_row, data_end_row,
                        row_count, column_count, null_cells_count, reported_total, reported_state_totals
                    ) VALUES %s;
                """, meta_records)

                # 2. raw_state_to_state_matrix
                df_s1 = tables["raw_state_to_state"]
                s1_records = []
                state_cols = [c for c in df_s1.columns if c != "to_state"]
                for r_idx, row in df_s1.iterrows():
                    to_state = row["to_state"]
                    source_r = 4 + r_idx
                    for c_idx, from_state in enumerate(state_cols, start=3):
                        val = row[from_state]
                        s1_records.append((
                            run_id, from_state, to_state,
                            float(val) if pd.notna(val) else None,
                            source_r, c_idx
                        ))
                execute_values(cur, """
                    INSERT INTO raw_state_to_state_matrix (
                        run_id, from_state, to_state, movement_value, source_row_index, source_col_index
                    ) VALUES %s;
                """, s1_records)
                staged_counts["raw_state_to_state_matrix"] = len(s1_records)

                # 3. raw_chapter_summary
                df_s2 = tables["raw_chapter_summary"]
                s2_records = []
                for r_idx, row in df_s2.iterrows():
                    val = row["value_inr_crore"]
                    s2_records.append((
                        run_id, row["chapter_code"], row["chapter_description"],
                        float(val) if pd.notna(val) else None,
                        3 + r_idx
                    ))
                execute_values(cur, """
                    INSERT INTO raw_chapter_summary (
                        run_id, chapter_code, chapter_description, movement_value, source_row_index
                    ) VALUES %s;
                """, s2_records)
                staged_counts["raw_chapter_summary"] = len(s2_records)

                # 4. raw_chapter_outward_matrix
                df_s3 = tables["raw_chapter_outward"]
                s3_records = []
                s3_states = [c for c in df_s3.columns if c not in ("chapter_code", "chapter_description")]
                for r_idx, row in df_s3.iterrows():
                    c_code = row["chapter_code"]
                    c_desc = row["chapter_description"]
                    source_r = 3 + r_idx
                    for s in s3_states:
                        val = row[s]
                        s3_records.append((
                            run_id, c_code, c_desc, s,
                            float(val) if pd.notna(val) else None,
                            source_r
                        ))
                execute_values(cur, """
                    INSERT INTO raw_chapter_outward_matrix (
                        run_id, chapter_code, chapter_description, state, movement_value, source_row_index
                    ) VALUES %s;
                """, s3_records)
                staged_counts["raw_chapter_outward_matrix"] = len(s3_records)

                # 5. raw_chapter_inward_matrix
                df_s4 = tables["raw_chapter_inward"]
                s4_records = []
                s4_cols = [c for c in df_s4.columns if c not in ("chapter_code", "chapter_description")]
                for r_idx, row in df_s4.iterrows():
                    c_code = row["chapter_code"]
                    c_desc = row["chapter_description"]
                    source_r = 3 + r_idx
                    for col_name in s4_cols:
                        val = row[col_name]
                        is_summary = (col_name == "TOTAL")
                        s4_records.append((
                            run_id, c_code, c_desc, col_name,
                            float(val) if pd.notna(val) else None,
                            is_summary, source_r
                        ))
                execute_values(cur, """
                    INSERT INTO raw_chapter_inward_matrix (
                        run_id, chapter_code, chapter_description, state, movement_value, is_summary_column, source_row_index
                    ) VALUES %s;
                """, s4_records)
                staged_counts["raw_chapter_inward_matrix"] = len(s4_records)

                # 6. raw_chapter_internal_matrix
                df_s5 = tables["raw_chapter_internal"]
                s5_records = []
                s5_cols = [c for c in df_s5.columns if c not in ("chapter_code", "chapter_description")]
                for r_idx, row in df_s5.iterrows():
                    c_code = row["chapter_code"]
                    c_desc = row["chapter_description"]
                    source_r = 3 + r_idx
                    for col_name in s5_cols:
                        val = row[col_name]
                        is_summary = (col_name == "TOTAL")
                        s5_records.append((
                            run_id, c_code, c_desc, col_name,
                            float(val) if pd.notna(val) else None,
                            is_summary, source_r
                        ))
                execute_values(cur, """
                    INSERT INTO raw_chapter_internal_matrix (
                        run_id, chapter_code, chapter_description, state, movement_value, is_summary_column, source_row_index
                    ) VALUES %s;
                """, s5_records)
                staged_counts["raw_chapter_internal_matrix"] = len(s5_records)

            conn.commit()
            return staged_counts
        finally:
            conn.close()

    def load_trusted_data(self, run_id: str, normalized_tables: Dict[str, pd.DataFrame]) -> Dict[str, int]:
        """Loads normalized 3NF DataFrames into trusted_* tables."""
        trusted_counts = {}
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                # Idempotency: clear previous trusted records for this run_id
                cur.execute("DELETE FROM trusted_state_chapter_internal WHERE run_id = %s::uuid;", (run_id,))
                cur.execute("DELETE FROM trusted_state_chapter_inward WHERE run_id = %s::uuid;", (run_id,))
                cur.execute("DELETE FROM trusted_state_chapter_outward WHERE run_id = %s::uuid;", (run_id,))
                cur.execute("DELETE FROM trusted_chapter_movement WHERE run_id = %s::uuid;", (run_id,))
                cur.execute("DELETE FROM trusted_state_movement WHERE run_id = %s::uuid;", (run_id,))

                # 1. trusted_state_movement
                df_sm = normalized_tables["state_movement"]
                sm_records = [
                    (run_id, r["origin_state"], r["destination_state"],
                     float(r["movement_value_inr_crore"]) if pd.notna(r["movement_value_inr_crore"]) else None)
                    for _, r in df_sm.iterrows()
                ]
                execute_values(cur, """
                    INSERT INTO trusted_state_movement (run_id, origin_state, destination_state, movement_value_inr_crore)
                    VALUES %s;
                """, sm_records)
                trusted_counts["trusted_state_movement"] = len(sm_records)

                # 2. trusted_chapter_movement
                df_cm = normalized_tables["chapter_movement"]
                cm_records = [
                    (run_id, r["chapter_code"], r["chapter_description"],
                     float(r["movement_value_inr_crore"]) if pd.notna(r["movement_value_inr_crore"]) else None)
                    for _, r in df_cm.iterrows()
                ]
                execute_values(cur, """
                    INSERT INTO trusted_chapter_movement (run_id, chapter_code, chapter_description, movement_value_inr_crore)
                    VALUES %s;
                """, cm_records)
                trusted_counts["trusted_chapter_movement"] = len(cm_records)

                # 3. trusted_state_chapter_outward
                df_sco = normalized_tables["state_chapter_outward"]
                sco_records = [
                    (run_id, r["chapter_code"], r["chapter_description"], r["state"],
                     float(r["movement_value_inr_crore"]) if pd.notna(r["movement_value_inr_crore"]) else None)
                    for _, r in df_sco.iterrows()
                ]
                execute_values(cur, """
                    INSERT INTO trusted_state_chapter_outward (run_id, chapter_code, chapter_description, state, movement_value_inr_crore)
                    VALUES %s;
                """, sco_records)
                trusted_counts["trusted_state_chapter_outward"] = len(sco_records)

                # 4. trusted_state_chapter_inward
                df_sci = normalized_tables["state_chapter_inward"]
                sci_records = [
                    (run_id, r["chapter_code"], r["chapter_description"], r["state"],
                     float(r["movement_value_inr_crore"]) if pd.notna(r["movement_value_inr_crore"]) else None)
                    for _, r in df_sci.iterrows()
                ]
                execute_values(cur, """
                    INSERT INTO trusted_state_chapter_inward (run_id, chapter_code, chapter_description, state, movement_value_inr_crore)
                    VALUES %s;
                """, sci_records)
                trusted_counts["trusted_state_chapter_inward"] = len(sci_records)

                # 5. trusted_state_chapter_internal
                df_scint = normalized_tables["state_chapter_internal"]
                scint_records = [
                    (run_id, r["chapter_code"], r["chapter_description"], r["state"],
                     float(r["movement_value_inr_crore"]) if pd.notna(r["movement_value_inr_crore"]) else None)
                    for _, r in df_scint.iterrows()
                ]
                execute_values(cur, """
                    INSERT INTO trusted_state_chapter_internal (run_id, chapter_code, chapter_description, state, movement_value_inr_crore)
                    VALUES %s;
                """, scint_records)
                trusted_counts["trusted_state_chapter_internal"] = len(scint_records)

            conn.commit()
            return trusted_counts
        finally:
            conn.close()

    def record_validation_results(self, run_id: str, results: List[Any]) -> int:
        """Persists validation results into validation_results table."""
        records = []
        for r in results:
            # handle both ValidationCheckResult object and dict
            d = r.to_dict() if hasattr(r, "to_dict") else r
            records.append((
                run_id,
                d["check_id"],
                d["check_category"],
                d["check_name"],
                d["table_name"],
                d["status"],
                d["severity"],
                str(d.get("expected")),
                str(d.get("observed")),
                d.get("difference"),
                d.get("affected_records", 0),
                d["message"],
                d.get("execution_timestamp")
            ))

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM validation_results WHERE run_id = %s::uuid;", (run_id,))
                execute_values(cur, """
                    INSERT INTO validation_results (
                        run_id, check_id, check_category, check_name, table_name,
                        status, severity, expected_value, observed_value, difference,
                        affected_records, message, executed_at
                    ) VALUES %s;
                """, records)
            conn.commit()
            return len(records)
        finally:
            conn.close()

    def record_reconciliation_results(self, run_id: str, results: List[Any]) -> int:
        """Persists cross-table reconciliation results into reconciliation_results table."""
        records = []
        for r in results:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            records.append((
                run_id,
                d["rule_code"],
                d.get("rule_category", "DATA-OBSERVED"),
                d["source_tables"],
                d["dimension"],
                d["entity"],
                d.get("expected_value"),
                d.get("observed_value"),
                d.get("absolute_difference"),
                d.get("relative_difference"),
                d.get("absolute_tolerance"),
                d.get("relative_tolerance"),
                d["status"],
                d["severity"],
                d["message"],
                d.get("executed_at")
            ))

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM reconciliation_results WHERE run_id = %s::uuid;", (run_id,))
                execute_values(cur, """
                    INSERT INTO reconciliation_results (
                        run_id, rule_code, rule_category, source_tables, dimension,
                        entity, expected_value, observed_value, absolute_difference,
                        relative_difference, absolute_tolerance, relative_tolerance,
                        status, severity, message, executed_at
                    ) VALUES %s;
                """, records)
            conn.commit()
            return len(records)
        finally:
            conn.close()

    def record_statistical_results(self, run_id: str, results: List[Any]) -> int:
        """Persists Year-over-Year statistical results into statistical_results table."""
        records = []
        for r in results:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            records.append((
                run_id,
                d.get("comparison_year", "2023-24"),
                d.get("reference_year", "2022-23"),
                d["dimension"],
                d["metric"],
                d["test_method"],
                d.get("sample_size_reference"),
                d.get("sample_size_comparison"),
                d.get("statistic"),
                d.get("p_value"),
                d.get("alpha"),
                d.get("psi_value"),
                d.get("psi_threshold"),
                d["status"],
                d["interpretation"],
                d.get("executed_at")
            ))

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM statistical_results WHERE run_id = %s::uuid;", (run_id,))
                execute_values(cur, """
                    INSERT INTO statistical_results (
                        run_id, comparison_year, reference_year, dimension, metric,
                        test_method, sample_size_reference, sample_size_comparison,
                        statistic, p_value, alpha, psi_value, psi_threshold,
                        status, interpretation, executed_at
                    ) VALUES %s;
                """, records)
            conn.commit()
            return len(records)
        finally:
            conn.close()



