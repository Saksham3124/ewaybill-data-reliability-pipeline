"""
transformation/normalizer.py
----------------------------
Normalization module converting raw E-Way Bill extracted matrices into
clean Third Normal Form (3NF) relational tables.

Governance Constraints:
1. Strict schema compliance: Only the requested fields are created.
   - Do NOT invent additional business fields.
2. Preserves source blanks/NULLs (no global 0 imputation).
3. Preserves exact data types: string for states/chapters, float/None for values.
"""

from typing import Dict, Any, List
import pandas as pd


class EwayBillNormalizer:
    """Normalizes raw E-Way Bill tables into relational representations."""

    def __init__(self, raw_tables: Dict[str, pd.DataFrame]):
        self.raw_tables = raw_tables

    def normalize_all(self) -> Dict[str, pd.DataFrame]:
        """Runs normalization across all 5 raw tables."""
        return {
            "state_movement": self.normalize_state_movement(),
            "chapter_movement": self.normalize_chapter_movement(),
            "state_chapter_outward": self.normalize_state_chapter_outward(),
            "state_chapter_inward": self.normalize_state_chapter_inward(),
            "state_chapter_internal": self.normalize_state_chapter_internal()
        }

    def normalize_state_movement(self) -> pd.DataFrame:
        """
        Normalizes Table I (State-to-State square matrix) into:
        - origin_state
        - destination_state
        - movement_value_inr_crore

        Columns in Table I represent 'From State' (origin_state).
        Rows in Table I represent 'To State' (destination_state).
        """
        df_raw = self.raw_tables["raw_state_to_state"]
        state_cols = [c for c in df_raw.columns if c != "to_state"]

        records: List[Dict[str, Any]] = []
        for _, row in df_raw.iterrows():
            dest_state = row["to_state"]
            for orig_state in state_cols:
                val = row[orig_state]
                records.append({
                    "origin_state": orig_state,
                    "destination_state": dest_state,
                    "movement_value_inr_crore": val  # Preserves None/NaN if blank
                })

        df_norm = pd.DataFrame(records)
        return df_norm

    def normalize_chapter_movement(self) -> pd.DataFrame:
        """
        Normalizes Table II (Chapter summary) into:
        - chapter_code
        - chapter_description
        - movement_value_inr_crore
        """
        df_raw = self.raw_tables["raw_chapter_summary"]
        df_norm = df_raw[["chapter_code", "chapter_description", "value_inr_crore"]].copy()
        df_norm.rename(columns={"value_inr_crore": "movement_value_inr_crore"}, inplace=True)
        return df_norm

    def normalize_state_chapter_outward(self) -> pd.DataFrame:
        """
        Normalizes Table III (Chapter x Origin State outward matrix) into:
        - chapter_code
        - chapter_description
        - state
        - movement_value_inr_crore
        """
        df_raw = self.raw_tables["raw_chapter_outward"]
        state_cols = [c for c in df_raw.columns if c not in ("chapter_code", "chapter_description")]

        records: List[Dict[str, Any]] = []
        for _, row in df_raw.iterrows():
            c_code = row["chapter_code"]
            c_desc = row["chapter_description"]
            for state_name in state_cols:
                records.append({
                    "chapter_code": c_code,
                    "chapter_description": c_desc,
                    "state": state_name,
                    "movement_value_inr_crore": row[state_name]
                })

        df_norm = pd.DataFrame(records)
        return df_norm

    def normalize_state_chapter_inward(self) -> pd.DataFrame:
        """
        Normalizes Table IV (Chapter x Destination State inward matrix) into:
        - chapter_code
        - chapter_description
        - state
        - movement_value_inr_crore

        Note: Excludes the 'TOTAL' column as it is a summary aggregate, not a state.
        """
        df_raw = self.raw_tables["raw_chapter_inward"]
        state_cols = [c for c in df_raw.columns if c not in ("chapter_code", "chapter_description", "TOTAL")]

        records: List[Dict[str, Any]] = []
        for _, row in df_raw.iterrows():
            c_code = row["chapter_code"]
            c_desc = row["chapter_description"]
            for state_name in state_cols:
                records.append({
                    "chapter_code": c_code,
                    "chapter_description": c_desc,
                    "state": state_name,
                    "movement_value_inr_crore": row[state_name]
                })

        df_norm = pd.DataFrame(records)
        return df_norm

    def normalize_state_chapter_internal(self) -> pd.DataFrame:
        """
        Normalizes Table V (Chapter x State internal matrix) into:
        - chapter_code
        - chapter_description
        - state
        - movement_value_inr_crore

        Note: Excludes the 'TOTAL' column as it is a summary aggregate, not a state.
        """
        df_raw = self.raw_tables["raw_chapter_internal"]
        state_cols = [c for c in df_raw.columns if c not in ("chapter_code", "chapter_description", "TOTAL")]

        records: List[Dict[str, Any]] = []
        for _, row in df_raw.iterrows():
            c_code = row["chapter_code"]
            c_desc = row["chapter_description"]
            for state_name in state_cols:
                records.append({
                    "chapter_code": c_code,
                    "chapter_description": c_desc,
                    "state": state_name,
                    "movement_value_inr_crore": row[state_name]
                })

        df_norm = pd.DataFrame(records)
        return df_norm
