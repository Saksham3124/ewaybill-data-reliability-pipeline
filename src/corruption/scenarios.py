"""
src/corruption/scenarios.py
---------------------------
Deterministic scenario definitions and data corruptors for Phase 7.
Every scenario operates on an isolated deep copy of clean data.
Original source workbooks remain byte-for-byte untouched.
"""

import copy
from typing import Dict, Any, Tuple, List
import pandas as pd
import numpy as np

from src.corruption.models import CorruptionScenario, CorruptionType


def get_scenario_definitions() -> Dict[str, CorruptionScenario]:
    """Returns canonical definitions of the 7 controlled corruption scenarios."""
    return {
        "CORRUPT-A": CorruptionScenario(
            scenario_id="CORRUPT-A",
            corruption_type=CorruptionType.MISSING_RECORD.value,
            expected_detector="COMPLETENESS_VALIDATION (CMP-03)",
            description="Remove single logical record (Chapter 10, MAHARASHTRA) from state_chapter_outward.",
            source_year="2023-24",
            source_table="state_chapter_outward",
            target_field="(chapter_code, state)",
            target_record="chapter_code='10', state='MAHARASHTRA'",
            original_value="Record present (1 row out of 2,970)",
            corrupted_value="Record removed (2,969 rows remaining)",
            random_seed=None
        ),
        "CORRUPT-B": CorruptionScenario(
            scenario_id="CORRUPT-B",
            corruption_type=CorruptionType.DUPLICATE_RECORD.value,
            expected_detector="UNIQUENESS_VALIDATION (UNQ-03)",
            description="Duplicate logically unique record (Chapter 10, MAHARASHTRA) in state_chapter_outward.",
            source_year="2023-24",
            source_table="state_chapter_outward",
            target_field="(chapter_code, state)",
            target_record="chapter_code='10', state='MAHARASHTRA'",
            original_value="1 unique record",
            corrupted_value="2 identical records (duplicate row appended, 2,971 rows total)",
            random_seed=None
        ),
        "CORRUPT-C": CorruptionScenario(
            scenario_id="CORRUPT-C",
            corruption_type=CorruptionType.INVALID_DOMAIN.value,
            expected_detector="DOMAIN_VALIDATION (DOM-03)",
            description="Mutate valid HS chapter code '10' into invalid 3-digit code '999' in chapter_movement.",
            source_year="2023-24",
            source_table="chapter_movement",
            target_field="chapter_code",
            target_record="chapter_code='10'",
            original_value="'10'",
            corrupted_value="'999'",
            random_seed=None
        ),
        "CORRUPT-D": CorruptionScenario(
            scenario_id="CORRUPT-D",
            corruption_type=CorruptionType.ALTERED_NUMERIC.value,
            expected_detector="SOURCE_TOTAL_VALIDATION (REC-V02) / RECONCILIATION (REC-DO02, REC-DO05)",
            description="Inject +500.00 Cr into Chapter 10 MAHARASHTRA outward movement without modifying summary total row.",
            source_year="2023-24",
            source_table="raw_chapter_outward",
            target_field="MAHARASHTRA",
            target_record="chapter_code='10'",
            original_value=1687.5131552319997,
            corrupted_value=2187.5131552319997,
            random_seed=None
        ),
        "CORRUPT-E": CorruptionScenario(
            scenario_id="CORRUPT-E",
            corruption_type=CorruptionType.MISSING_ENTITY_COLUMN.value,
            expected_detector="COMPLETENESS_VALIDATION (CMP-03) / RECONCILIATION",
            description="Remove state entity column 'BIHAR' entirely from Table III (outward movement), while retaining it elsewhere.",
            source_year="2023-24",
            source_table="raw_chapter_outward",
            target_field="Column 'BIHAR'",
            target_record="All 90 chapter dispatches for BIHAR",
            original_value="Column 'BIHAR' present (90 rows)",
            corrupted_value="Column 'BIHAR' dropped (leaving 32 state columns, 2,880 rows)",
            random_seed=None
        ),
        "CORRUPT-F": CorruptionScenario(
            scenario_id="CORRUPT-F",
            corruption_type=CorruptionType.NUMERIC_TO_TEXT.value,
            expected_detector="NUMERIC_VALIDATION (NUM-01)",
            description="Convert numeric float value to non-numeric string 'CORRUPTED_TEXT' in state_chapter_internal.",
            source_year="2023-24",
            source_table="state_chapter_internal",
            target_field="movement_value_inr_crore",
            target_record="chapter_code='10', state='MAHARASHTRA'",
            original_value=1457.697261449,
            corrupted_value="CORRUPTED_TEXT",
            random_seed=None
        ),
        "CORRUPT-G": CorruptionScenario(
            scenario_id="CORRUPT-G",
            corruption_type=CorruptionType.DISTRIBUTION_SHIFT.value,
            expected_detector="STATISTICAL_ANALYSIS (KS_TEST / PSI)",
            description="Apply 100x scale divergence to state outward freight volumes in FY 2023–24 comparison distribution.",
            source_year="2023-24",
            source_table="state_outward",
            target_field="State Outward Freight Distribution",
            target_record="All 33 state outward dispatch volumes",
            original_value="Baseline distribution (KS p = 0.6543 vs FY 2022–23; PSI = 0.2341)",
            corrupted_value="Shifted distribution (100x scaling; KS p < 1e-7, PSI = 3.0118 >= 0.25)",
            random_seed=None
        )
    }


def deepcopy_dataset(
    raw_data: Dict[str, Any],
    normalized_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Creates a deep copy of in-memory data structures to guarantee test isolation."""
    copied_raw = {
        "metadata": copy.deepcopy(raw_data.get("metadata", {})),
        "tables": {k: df.copy(deep=True) for k, df in raw_data["tables"].items()}
    }
    copied_norm = {k: df.copy(deep=True) for k, df in normalized_tables.items()}
    return copied_raw, copied_norm


# -----------------------------------------------------------------------------
# Scenario Transformers
# -----------------------------------------------------------------------------

def apply_scenario_a(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario A: Remove (chapter_code='10', state='MAHARASHTRA') from state_chapter_outward."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df = norm_c["state_chapter_outward"]
    mask = (df["chapter_code"] == "10") & (df["state"] == "MAHARASHTRA")
    norm_c["state_chapter_outward"] = df[~mask].reset_index(drop=True)
    return raw_c, norm_c


def apply_scenario_b(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario B: Duplicate (chapter_code='10', state='MAHARASHTRA') in state_chapter_outward."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df = norm_c["state_chapter_outward"]
    target_row = df[(df["chapter_code"] == "10") & (df["state"] == "MAHARASHTRA")].copy()
    norm_c["state_chapter_outward"] = pd.concat([df, target_row], ignore_index=True)
    return raw_c, norm_c


def apply_scenario_c(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario C: Mutate chapter_code '10' to '999' in chapter_movement."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df = norm_c["chapter_movement"].copy()
    df.loc[df["chapter_code"] == "10", "chapter_code"] = "999"
    norm_c["chapter_movement"] = df
    return raw_c, norm_c


def apply_scenario_d(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario D: Inject +500.0 Cr in Table III (outward) Chapter 10 MAHARASHTRA without updating total."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df_s3 = raw_c["tables"]["raw_chapter_outward"].copy()
    # Row for chapter 10
    idx = df_s3[df_s3["chapter_code"].astype(str) == "10"].index[0]
    df_s3.at[idx, "MAHARASHTRA"] = float(df_s3.at[idx, "MAHARASHTRA"]) + 500.0
    raw_c["tables"]["raw_chapter_outward"] = df_s3

    # Also update normalized table to reflect corrupted raw table
    df_norm = norm_c["state_chapter_outward"].copy()
    n_idx = df_norm[(df_norm["chapter_code"] == "10") & (df_norm["state"] == "MAHARASHTRA")].index[0]
    df_norm.at[n_idx, "movement_value_inr_crore"] = float(df_norm.at[n_idx, "movement_value_inr_crore"]) + 500.0
    norm_c["state_chapter_outward"] = df_norm
    return raw_c, norm_c


def apply_scenario_e(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario E: Remove state column 'BIHAR' from Table III raw table and normalized table."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df_s3 = raw_c["tables"]["raw_chapter_outward"].copy()
    if "BIHAR" in df_s3.columns:
        df_s3 = df_s3.drop(columns=["BIHAR"])
    raw_c["tables"]["raw_chapter_outward"] = df_s3

    df_norm = norm_c["state_chapter_outward"].copy()
    df_norm = df_norm[df_norm["state"] != "BIHAR"].reset_index(drop=True)
    norm_c["state_chapter_outward"] = df_norm
    return raw_c, norm_c


def apply_scenario_f(
    raw_data: Dict[str, Any],
    norm_tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame]]:
    """Scenario F: Set movement_value_inr_crore = 'CORRUPTED_TEXT' in state_chapter_internal."""
    raw_c, norm_c = deepcopy_dataset(raw_data, norm_tables)
    df_norm = norm_c["state_chapter_internal"].copy()
    # Find chapter 10, MAHARASHTRA
    idx = df_norm[(df_norm["chapter_code"] == "10") & (df_norm["state"] == "MAHARASHTRA")].index[0]
    # Set to object/string
    df_norm["movement_value_inr_crore"] = df_norm["movement_value_inr_crore"].astype(object)
    df_norm.at[idx, "movement_value_inr_crore"] = "CORRUPTED_TEXT"
    norm_c["state_chapter_internal"] = df_norm
    return raw_c, norm_c


def apply_scenario_g(
    raw_22: Dict[str, Any],
    raw_24: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Scenario G: Introduce controlled 100x scale shift in FY 2023–24 state outward dispatches."""
    raw_22_c = {
        "metadata": copy.deepcopy(raw_22.get("metadata", {})),
        "tables": {k: df.copy(deep=True) for k, df in raw_22["tables"].items()}
    }
    raw_24_c = {
        "metadata": copy.deepcopy(raw_24.get("metadata", {})),
        "tables": {k: df.copy(deep=True) for k, df in raw_24["tables"].items()}
    }

    # Scale all state outward columns by 100.0 in 2023-24
    df_s3 = raw_24_c["tables"]["raw_chapter_outward"].copy()
    state_cols = [c for c in df_s3.columns if c not in ("chapter_code", "chapter_description", "TOTAL", "VALUE (in INR Crore)")]
    for st in state_cols:
        df_s3[st] = df_s3[st] * 100.0
    raw_24_c["tables"]["raw_chapter_outward"] = df_s3

    return raw_22_c, raw_24_c
