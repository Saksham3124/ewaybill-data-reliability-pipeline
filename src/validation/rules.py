"""
validation/rules.py
-------------------
Mathematical Validation Engine for E-Way Bill intra-table checks (REC-V01 to REC-V08).

Governance Constraints:
1. Approves REC-V01 through REC-V08 as intra-table mathematical verification checks.
2. Uses configurable tolerances (via ReconciliationConfig).
3. Any calculation that treats NULL as zero explicitly documents that treatment at calculation level.
4. Preserves distinction between DOCUMENTED BY OFFICIAL SOURCE, OBSERVED FROM DATA, and INFERENCE.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.reconciliation.config import ReconciliationConfig, DEFAULT_CONFIG


@dataclass
class ValidationResult:
    """Represents the execution outcome of an intra-table validation rule."""
    rule_id: str
    rule_name: str
    classification: str
    source_table: str
    status: str  # "PASS" or "FAIL"
    expected_value: float
    observed_value: float
    difference: float
    tolerance: float
    details: Dict[str, Any]
    governance_note: str


class IntraTableValidator:
    """Executes verified intra-table mathematical checks (REC-V01 through REC-V08)."""

    def __init__(self, raw_data: Dict[str, Any], config: Optional[ReconciliationConfig] = None):
        self.raw_data = raw_data
        self.tables = raw_data["tables"]
        self.metadata = raw_data["metadata"]
        self.config = config or DEFAULT_CONFIG

    def run_all_verified_checks(self) -> List[ValidationResult]:
        """Runs all 8 approved intra-table validation rules."""
        return [
            self.check_rec_v01(),
            self.check_rec_v02(),
            self.check_rec_v03(),
            self.check_rec_v04(),
            self.check_rec_v05(),
            self.check_rec_v06(),
            self.check_rec_v07(),
            self.check_rec_v08(),
        ]

    def check_rec_v01(self) -> ValidationResult:
        """
        REC-V01: Table II Chapter Row Summation vs. Row 93 Total.
        [DOCUMENTED BY OFFICIAL SOURCE] Table II explicitly reports 'TOTAL VALUE' in Row 93.
        """
        df = self.tables["raw_chapter_summary"]
        reported_total = self.metadata["worksheets"]["Tab II_Chap_Revised_Road"]["reported_total_row_93"]

        # Sum of non-null chapter values (no nulls exist in Table II)
        computed_sum = float(df["value_inr_crore"].dropna().sum())
        diff = abs(computed_sum - reported_total)
        tol = self.config.float_tolerance

        return ValidationResult(
            rule_id="REC-V01",
            rule_name="Table II Chapter Row Summation",
            classification="VERIFIED",
            source_table="Tab II_Chap_Revised_Road",
            status="PASS" if diff <= tol else "FAIL",
            expected_value=reported_total,
            observed_value=computed_sum,
            difference=diff,
            tolerance=tol,
            details={"chapter_count": len(df)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Directly verifies the reported national total against individual chapter rows."
        )

    def check_rec_v02(self) -> ValidationResult:
        """
        REC-V02: Table III Chapter Rows Summation vs. Row 93 State Outward Totals.
        [DOCUMENTED BY OFFICIAL SOURCE] Table III explicitly reports 'OUTWARD VALUE' in Row 93 per state.
        
        TREATMENT OF NULL:
        Source empty cells (None) are treated as 0.0 at this calculation level to compute
        the column sum for verification against the published state outward total.
        """
        df = self.tables["raw_chapter_outward"]
        meta = self.metadata["worksheets"]["Tab III_Outward_Revised_Road"]
        states = meta["states"]
        reported_totals = meta["reported_state_totals_row_93"]

        max_diff = 0.0
        state_diffs = {}
        for s in states:
            # Explicit treatment: fillna(0.0) at calculation level only
            col_sum = float(df[s].fillna(0.0).sum())
            expected = reported_totals[s]
            d = abs(col_sum - expected)
            state_diffs[s] = d
            if d > max_diff:
                max_diff = d

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V02",
            rule_name="Table III State Outward Column Summation",
            classification="VERIFIED",
            source_table="Tab III_Outward_Revised_Road",
            status="PASS" if max_diff <= tol else "FAIL",
            expected_value=0.0,
            observed_value=max_diff,
            difference=max_diff,
            tolerance=tol,
            details={"max_state_difference": max_diff, "evaluated_states_count": len(states)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Null cells explicitly treated as 0.0 at calculation level to sum chapter dispatches per state."
        )

    def check_rec_v03(self) -> ValidationResult:
        """
        REC-V03: Table IV Chapter Rows Summation vs. Row 93 State Inward Totals.
        [DOCUMENTED BY OFFICIAL SOURCE] Table IV explicitly reports 'INWARD VALUE' in Row 93 per state.
        
        TREATMENT OF NULL:
        Source empty cells (None) are treated as 0.0 at this calculation level to compute
        the column sum for verification against the published state inward total.
        """
        df = self.tables["raw_chapter_inward"]
        meta = self.metadata["worksheets"]["Tab IV_Inward_Revised_Road"]
        states = meta["states"]
        reported_totals = meta["reported_state_totals_row_93"]

        max_diff = 0.0
        for s in states:
            col_sum = float(df[s].fillna(0.0).sum())
            expected = reported_totals[s]
            d = abs(col_sum - expected)
            if d > max_diff:
                max_diff = d

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V03",
            rule_name="Table IV State Inward Column Summation",
            classification="VERIFIED",
            source_table="Tab IV_Inward_Revised_Road",
            status="PASS" if max_diff <= tol else "FAIL",
            expected_value=0.0,
            observed_value=max_diff,
            difference=max_diff,
            tolerance=tol,
            details={"max_state_difference": max_diff, "evaluated_states_count": len(states)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Null cells explicitly treated as 0.0 at calculation level to sum chapter receipts per state."
        )

    def check_rec_v04(self) -> ValidationResult:
        """
        REC-V04: Table IV State Columns Summation vs. Column AK Chapter Totals.
        [DOCUMENTED BY OFFICIAL SOURCE] Table IV explicitly provides a 'TOTAL' column (Col AK).
        
        TREATMENT OF NULL:
        Source empty cells (None) are treated as 0.0 at this calculation level to compute
        the row sum for verification against the published chapter inward total.
        """
        df = self.tables["raw_chapter_inward"]
        meta = self.metadata["worksheets"]["Tab IV_Inward_Revised_Road"]
        states = meta["states"]

        # Horizontal sum of state columns across each row
        computed_row_sums = df[states].fillna(0.0).sum(axis=1)
        reported_totals = df["TOTAL"].fillna(0.0)
        max_diff = float((computed_row_sums - reported_totals).abs().max())

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V04",
            rule_name="Table IV Chapter Inward Row Summation",
            classification="VERIFIED",
            source_table="Tab IV_Inward_Revised_Road",
            status="PASS" if max_diff <= tol else "FAIL",
            expected_value=0.0,
            observed_value=max_diff,
            difference=max_diff,
            tolerance=tol,
            details={"max_chapter_difference": max_diff, "chapter_count": len(df)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Null cells explicitly treated as 0.0 at calculation level to sum state arrivals per chapter."
        )

    def check_rec_v05(self) -> ValidationResult:
        """
        REC-V05: Table IV Dual-Dimension Grand Total Cross-Foot.
        [DOCUMENTED BY OFFICIAL SOURCE] Row 93 and Column AK intersect at Cell AK93.
        """
        meta = self.metadata["worksheets"]["Tab IV_Inward_Revised_Road"]
        states = meta["states"]
        reported_state_totals = meta["reported_state_totals_row_93"]
        grand_total_ak93 = meta["reported_grand_total_cell_ak93"]

        sum_state_totals = sum(reported_state_totals[s] for s in states)
        diff = abs(sum_state_totals - grand_total_ak93)

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V05",
            rule_name="Table IV Grand Total Cross-Foot",
            classification="VERIFIED",
            source_table="Tab IV_Inward_Revised_Road",
            status="PASS" if diff <= tol else "FAIL",
            expected_value=grand_total_ak93,
            observed_value=sum_state_totals,
            difference=diff,
            tolerance=tol,
            details={"sum_of_state_totals": sum_state_totals, "cell_ak93": grand_total_ak93},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Verifies dual-axis cross-foot balance into Cell AK93."
        )

    def check_rec_v06(self) -> ValidationResult:
        """
        REC-V06: Table V Chapter Rows Summation vs. Row 93 State Internal Totals.
        [DOCUMENTED BY OFFICIAL SOURCE] Table V explicitly reports 'INTERNAL VALUE' in Row 93 per state.
        
        TREATMENT OF NULL:
        Source empty cells (None) are treated as 0.0 at this calculation level to compute
        the column sum for verification against the published state internal total.
        """
        df = self.tables["raw_chapter_internal"]
        meta = self.metadata["worksheets"]["Tab V_Internal_Revised_Road"]
        states = meta["states"]
        reported_totals = meta["reported_state_totals_row_93"]

        max_diff = 0.0
        for s in states:
            col_sum = float(df[s].fillna(0.0).sum())
            expected = reported_totals[s]
            d = abs(col_sum - expected)
            if d > max_diff:
                max_diff = d

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V06",
            rule_name="Table V State Internal Column Summation",
            classification="VERIFIED",
            source_table="Tab V_Internal_Revised_Road",
            status="PASS" if max_diff <= tol else "FAIL",
            expected_value=0.0,
            observed_value=max_diff,
            difference=max_diff,
            tolerance=tol,
            details={"max_state_difference": max_diff, "evaluated_states_count": len(states)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Null cells explicitly treated as 0.0 at calculation level to sum internal dispatches per state."
        )

    def check_rec_v07(self) -> ValidationResult:
        """
        REC-V07: Table V State Columns Summation vs. Column AK Chapter Totals.
        [DOCUMENTED BY OFFICIAL SOURCE] Table V explicitly provides a 'TOTAL' column (Col AK).
        
        TREATMENT OF NULL:
        Source empty cells (None) are treated as 0.0 at this calculation level to compute
        the row sum for verification against the published chapter internal total.
        """
        df = self.tables["raw_chapter_internal"]
        meta = self.metadata["worksheets"]["Tab V_Internal_Revised_Road"]
        states = meta["states"]

        computed_row_sums = df[states].fillna(0.0).sum(axis=1)
        reported_totals = df["TOTAL"].fillna(0.0)
        max_diff = float((computed_row_sums - reported_totals).abs().max())

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V07",
            rule_name="Table V Chapter Internal Row Summation",
            classification="VERIFIED",
            source_table="Tab V_Internal_Revised_Road",
            status="PASS" if max_diff <= tol else "FAIL",
            expected_value=0.0,
            observed_value=max_diff,
            difference=max_diff,
            tolerance=tol,
            details={"max_chapter_difference": max_diff, "chapter_count": len(df)},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Null cells explicitly treated as 0.0 at calculation level to sum internal flows per chapter."
        )

    def check_rec_v08(self) -> ValidationResult:
        """
        REC-V08: Table V Dual-Dimension Grand Total Cross-Foot.
        [DOCUMENTED BY OFFICIAL SOURCE] Row 93 and Column AK intersect at Cell AK93.
        """
        meta = self.metadata["worksheets"]["Tab V_Internal_Revised_Road"]
        states = meta["states"]
        reported_state_totals = meta["reported_state_totals_row_93"]
        grand_total_ak93 = meta["reported_grand_total_cell_ak93"]

        sum_state_totals = sum(reported_state_totals[s] for s in states)
        diff = abs(sum_state_totals - grand_total_ak93)

        tol = self.config.float_tolerance
        return ValidationResult(
            rule_id="REC-V08",
            rule_name="Table V Grand Total Cross-Foot",
            classification="VERIFIED",
            source_table="Tab V_Internal_Revised_Road",
            status="PASS" if diff <= tol else "FAIL",
            expected_value=grand_total_ak93,
            observed_value=sum_state_totals,
            difference=diff,
            tolerance=tol,
            details={"sum_of_state_totals": sum_state_totals, "cell_ak93": grand_total_ak93},
            governance_note="[DOCUMENTED BY OFFICIAL SOURCE] Verifies dual-axis cross-foot balance into Cell AK93."
        )
