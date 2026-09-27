"""
reconciliation/engine.py
------------------------
Cross-Table Reconciliation Engine for DGCI&S Road E-Way Bill workbook.
Implements the six DATA-OBSERVED cross-table audits specified in docs/reconciliation_spec.md.

Governance & Architectural Rules:
1. These audits are ADVISORY cross-table audits, NOT blocking validation gates.
2. Statuses used: PASS, WARNING, UNRESOLVED. Discrepancies do NOT trigger blocking FAIL.
3. No semantic overreach: Computations report observed numerical agreement/divergence,
   without asserting unproven economic definitions.
4. NULL preservation: Source NULLs are preserved; treatment of NULL as 0.0 is isolated
   strictly to aggregation calculations and explicitly documented.
5. Tolerances: Uses configurable ReconciliationConfig (absolute & relative tolerances).
6. OTHER TERRITORY: Handled with distinct status 'UNRESOLVED' and exact documented message;
   never imputed, rebalanced, or force-balanced.
7. Rejection of unapproved rules: REC-NV01 to REC-NV04 are excluded.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

from src.reconciliation.config import ReconciliationConfig, DEFAULT_CONFIG
from src.reconciliation.models import (
    ReconciliationResult,
    ReconciliationStatus,
    ReconciliationSeverity
)


class ReconciliationEngine:
    """Executes advisory cross-table reconciliation audits on DGCI&S E-Way Bill data."""

    def __init__(self, config: Optional[ReconciliationConfig] = None):
        self.config = config or DEFAULT_CONFIG

    def run_all_reconciliations(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: Optional[str] = None
    ) -> List[ReconciliationResult]:
        """
        Executes all six DATA-OBSERVED reconciliation audits:
        - REC-DO01: Table I matrix total vs Table II national total
        - REC-DO02: National outward vs national inward
        - REC-DO03: National total partitioning (outward+internal & inward+internal)
        - REC-DO04: State column marginal conservation (33 jurisdictions)
        - REC-DO05: State row marginal conservation (33 jurisdictions)
        - REC-DO06: Table I diagonal vs Table V internal (32 PASS, 1 UNRESOLVED)
        """
        run_id = run_id or f"rec_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        results: List[ReconciliationResult] = []

        results.append(self.reconcile_rec_do01(raw_data, normalized_tables, run_id))
        results.append(self.reconcile_rec_do02(raw_data, normalized_tables, run_id))
        results.extend(self.reconcile_rec_do03(raw_data, normalized_tables, run_id))
        results.extend(self.reconcile_rec_do04(raw_data, normalized_tables, run_id))
        results.extend(self.reconcile_rec_do05(raw_data, normalized_tables, run_id))
        results.extend(self.reconcile_rec_do06(raw_data, normalized_tables, run_id))

        return results

    # =========================================================================
    # REC-DO01: Table I matrix total vs Table II national total
    # =========================================================================
    def reconcile_rec_do01(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> ReconciliationResult:
        """
        REC-DO01: Table I matrix total vs Table II national total.
        Formula: SUM(Table I movement matrix) vs Table II Row 93 national total.
        Calculation detail: Null values in Table I are treated as 0.0 at calculation level only.
        """
        df_sm = normalized_tables["state_movement"]
        # Sum Table I movement values (NULLs treated as 0.0 at calculation level only)
        observed_val = float(df_sm["movement_value_inr_crore"].fillna(0.0).sum())

        # Expected: Table II published national total
        ws_ii_meta = raw_data["metadata"]["worksheets"].get("Tab II_Chap_Revised_Road", {})
        expected_val = float(ws_ii_meta.get("reported_total_row_93") or self.config.expected_published_national_total)

        abs_diff = abs(observed_val - expected_val)
        rel_diff = abs_diff / abs(expected_val) if expected_val != 0 else 0.0

        is_match = (abs_diff <= self.config.absolute_tolerance) or (rel_diff <= self.config.relative_tolerance)
        status = ReconciliationStatus.PASS.value if is_match else ReconciliationStatus.WARNING.value
        severity = ReconciliationSeverity.INFO.value if is_match else ReconciliationSeverity.WARNING.value

        msg = (
            f"Table I 33x33 matrix sum ({observed_val:,.2f} Cr) numerically agrees with Table II "
            f"national total ({expected_val:,.2f} Cr) within tolerance."
            if is_match else
            f"Discrepancy detected: Table I matrix sum ({observed_val:,.2f} Cr) differs from Table II "
            f"national total ({expected_val:,.2f} Cr) by {abs_diff:,.6f} Cr."
        )

        return ReconciliationResult(
            run_id=run_id,
            rule_code="REC-DO01",
            rule_category="DATA-OBSERVED",
            source_tables="Tab I_Stat_to_Stat_Revised_Road, Tab II_Chap_Revised_Road",
            dimension="NATIONAL",
            entity="NATIONAL",
            expected_value=expected_val,
            observed_value=observed_val,
            absolute_difference=abs_diff,
            relative_difference=rel_diff,
            absolute_tolerance=self.config.absolute_tolerance,
            relative_tolerance=self.config.relative_tolerance,
            status=status,
            severity=severity,
            message=msg
        )

    # =========================================================================
    # REC-DO02: National outward vs national inward
    # =========================================================================
    def reconcile_rec_do02(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> ReconciliationResult:
        """
        REC-DO02: National outward vs national inward.
        Formula: SUM(Table III outward state totals) vs Table IV national inward grand total.
        Note: Observed mathematical relationship; not asserted as an official 'closed economy identity'.
        Calculation detail: Null values in Table III are treated as 0.0 at calculation level only.
        """
        df_sco = normalized_tables["state_chapter_outward"]
        # Sum Table III outward values (NULLs treated as 0.0 at calculation level only)
        observed_val = float(df_sco["movement_value_inr_crore"].fillna(0.0).sum())

        # Expected: Table IV published national grand total (Cell AK93)
        ws_iv_meta = raw_data["metadata"]["worksheets"].get("Tab IV_Inward_Revised_Road", {})
        expected_val = float(ws_iv_meta.get("reported_grand_total_cell_ak93") or self.config.expected_published_outward_total)

        abs_diff = abs(observed_val - expected_val)
        rel_diff = abs_diff / abs(expected_val) if expected_val != 0 else 0.0

        is_match = (abs_diff <= self.config.absolute_tolerance) or (rel_diff <= self.config.relative_tolerance)
        status = ReconciliationStatus.PASS.value if is_match else ReconciliationStatus.WARNING.value
        severity = ReconciliationSeverity.INFO.value if is_match else ReconciliationSeverity.WARNING.value

        msg = (
            f"Table III outward sum ({observed_val:,.2f} Cr) numerically agrees with Table IV "
            f"inward grand total ({expected_val:,.2f} Cr) within tolerance."
            if is_match else
            f"Discrepancy detected: Table III outward sum ({observed_val:,.2f} Cr) differs from Table IV "
            f"inward grand total ({expected_val:,.2f} Cr) by {abs_diff:,.6f} Cr."
        )

        return ReconciliationResult(
            run_id=run_id,
            rule_code="REC-DO02",
            rule_category="DATA-OBSERVED",
            source_tables="Tab III_Outward_Revised_Road, Tab IV_Inward_Revised_Road",
            dimension="NATIONAL",
            entity="NATIONAL",
            expected_value=expected_val,
            observed_value=observed_val,
            absolute_difference=abs_diff,
            relative_difference=rel_diff,
            absolute_tolerance=self.config.absolute_tolerance,
            relative_tolerance=self.config.relative_tolerance,
            status=status,
            severity=severity,
            message=msg
        )

    # =========================================================================
    # REC-DO03: National total partitioning
    # =========================================================================
    def reconcile_rec_do03(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> List[ReconciliationResult]:
        """
        REC-DO03: National total partitioning.
        Compares:
        1. Table II total vs (Table III total + Table V total)
        2. Table II total vs (Table IV total + Table V total)
        Records two distinct observations.
        Calculation detail: Null values treated as 0.0 at calculation level only.
        """
        results = []

        df_cm = normalized_tables["chapter_movement"]
        df_sco = normalized_tables["state_chapter_outward"]
        df_sci = normalized_tables["state_chapter_inward"]
        df_scint = normalized_tables["state_chapter_internal"]

        # Base values (NULLs treated as 0.0 at calculation level only)
        table_ii_total = float(df_cm["movement_value_inr_crore"].fillna(0.0).sum())
        table_iii_total = float(df_sco["movement_value_inr_crore"].fillna(0.0).sum())
        table_iv_total = float(df_sci["movement_value_inr_crore"].fillna(0.0).sum())
        table_v_total = float(df_scint["movement_value_inr_crore"].fillna(0.0).sum())

        # Observation 1: Table II vs Table III (Outward) + Table V (Internal)
        obs_1_sum = table_iii_total + table_v_total
        diff_1 = abs(obs_1_sum - table_ii_total)
        rel_diff_1 = diff_1 / abs(table_ii_total) if table_ii_total != 0 else 0.0
        match_1 = (diff_1 <= self.config.absolute_tolerance) or (rel_diff_1 <= self.config.relative_tolerance)

        results.append(ReconciliationResult(
            run_id=run_id,
            rule_code="REC-DO03",
            rule_category="DATA-OBSERVED",
            source_tables="Tab II_Chap_Revised_Road, Tab III_Outward_Revised_Road, Tab V_Internal_Revised_Road",
            dimension="OUTWARD_INTERNAL_PARTITION",
            entity="NATIONAL",
            expected_value=table_ii_total,
            observed_value=obs_1_sum,
            absolute_difference=diff_1,
            relative_difference=rel_diff_1,
            absolute_tolerance=self.config.absolute_tolerance,
            relative_tolerance=self.config.relative_tolerance,
            status=ReconciliationStatus.PASS.value if match_1 else ReconciliationStatus.WARNING.value,
            severity=ReconciliationSeverity.INFO.value if match_1 else ReconciliationSeverity.WARNING.value,
            message=(
                f"Table II national total ({table_ii_total:,.2f} Cr) numerically agrees with the sum "
                f"of Table III outward ({table_iii_total:,.2f} Cr) and Table V internal ({table_v_total:,.2f} Cr) within tolerance."
                if match_1 else
                f"Discrepancy detected: Table II national total ({table_ii_total:,.2f} Cr) differs from "
                f"Outward + Internal ({obs_1_sum:,.2f} Cr) by {diff_1:,.6f} Cr."
            )
        ))

        # Observation 2: Table II vs Table IV (Inward) + Table V (Internal)
        obs_2_sum = table_iv_total + table_v_total
        diff_2 = abs(obs_2_sum - table_ii_total)
        rel_diff_2 = diff_2 / abs(table_ii_total) if table_ii_total != 0 else 0.0
        match_2 = (diff_2 <= self.config.absolute_tolerance) or (rel_diff_2 <= self.config.relative_tolerance)

        results.append(ReconciliationResult(
            run_id=run_id,
            rule_code="REC-DO03",
            rule_category="DATA-OBSERVED",
            source_tables="Tab II_Chap_Revised_Road, Tab IV_Inward_Revised_Road, Tab V_Internal_Revised_Road",
            dimension="INWARD_INTERNAL_PARTITION",
            entity="NATIONAL",
            expected_value=table_ii_total,
            observed_value=obs_2_sum,
            absolute_difference=diff_2,
            relative_difference=rel_diff_2,
            absolute_tolerance=self.config.absolute_tolerance,
            relative_tolerance=self.config.relative_tolerance,
            status=ReconciliationStatus.PASS.value if match_2 else ReconciliationStatus.WARNING.value,
            severity=ReconciliationSeverity.INFO.value if match_2 else ReconciliationSeverity.WARNING.value,
            message=(
                f"Table II national total ({table_ii_total:,.2f} Cr) numerically agrees with the sum "
                f"of Table IV inward ({table_iv_total:,.2f} Cr) and Table V internal ({table_v_total:,.2f} Cr) within tolerance."
                if match_2 else
                f"Discrepancy detected: Table II national total ({table_ii_total:,.2f} Cr) differs from "
                f"Inward + Internal ({obs_2_sum:,.2f} Cr) by {diff_2:,.6f} Cr."
            )
        ))

        return results

    # =========================================================================
    # REC-DO04: State-level column marginal conservation
    # =========================================================================
    def reconcile_rec_do04(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> List[ReconciliationResult]:
        """
        REC-DO04: State-level column marginal conservation across all 33 jurisdictions.
        Formula: SUM(Table I column for state s) vs Table III outward total(s) + Table V internal total(s).
        Calculation detail: Null values in Table I, III, V are treated as 0.0 at calculation level only.
        """
        results = []
        df_sm = normalized_tables["state_movement"]
        df_sco = normalized_tables["state_chapter_outward"]
        df_scint = normalized_tables["state_chapter_internal"]

        for state in self.config.expected_states:
            # Table I origin column sum for state (NULLs treated as 0.0 at calculation level only)
            col_sum = float(df_sm[df_sm["origin_state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            # Table III outward total for state
            outward_tot = float(df_sco[df_sco["state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            # Table V internal total for state
            internal_tot = float(df_scint[df_scint["state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            expected_tot = outward_tot + internal_tot
            abs_diff = abs(col_sum - expected_tot)
            rel_diff = abs_diff / abs(expected_tot) if expected_tot != 0 else 0.0

            is_match = (abs_diff <= self.config.absolute_tolerance) or (rel_diff <= self.config.relative_tolerance)
            status = ReconciliationStatus.PASS.value if is_match else ReconciliationStatus.WARNING.value
            severity = ReconciliationSeverity.INFO.value if is_match else ReconciliationSeverity.WARNING.value

            msg = (
                f"Table I column sum for {state} ({col_sum:,.2f} Cr) numerically agrees with "
                f"Outward ({outward_tot:,.2f} Cr) + Internal ({internal_tot:,.2f} Cr) within tolerance."
                if is_match else
                f"Discrepancy for {state}: Table I column sum ({col_sum:,.2f} Cr) differs from "
                f"Outward + Internal ({expected_tot:,.2f} Cr) by {abs_diff:,.6f} Cr."
            )

            results.append(ReconciliationResult(
                run_id=run_id,
                rule_code="REC-DO04",
                rule_category="DATA-OBSERVED",
                source_tables="Tab I_Stat_to_Stat_Revised_Road, Tab III_Outward_Revised_Road, Tab V_Internal_Revised_Road",
                dimension="STATE_COLUMN_MARGINAL",
                entity=state,
                expected_value=expected_tot,
                observed_value=col_sum,
                absolute_difference=abs_diff,
                relative_difference=rel_diff,
                absolute_tolerance=self.config.absolute_tolerance,
                relative_tolerance=self.config.relative_tolerance,
                status=status,
                severity=severity,
                message=msg
            ))

        return results

    # =========================================================================
    # REC-DO05: State-level row marginal conservation
    # =========================================================================
    def reconcile_rec_do05(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> List[ReconciliationResult]:
        """
        REC-DO05: State-level row marginal conservation across all 33 jurisdictions.
        Formula: SUM(Table I row for state s) vs Table IV inward total(s) + Table V internal total(s).
        Calculation detail: Null values in Table I, IV, V are treated as 0.0 at calculation level only.
        """
        results = []
        df_sm = normalized_tables["state_movement"]
        df_sci = normalized_tables["state_chapter_inward"]
        df_scint = normalized_tables["state_chapter_internal"]

        for state in self.config.expected_states:
            # Table I destination row sum for state (NULLs treated as 0.0 at calculation level only)
            row_sum = float(df_sm[df_sm["destination_state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            # Table IV inward total for state
            inward_tot = float(df_sci[df_sci["state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            # Table V internal total for state
            internal_tot = float(df_scint[df_scint["state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            expected_tot = inward_tot + internal_tot
            abs_diff = abs(row_sum - expected_tot)
            rel_diff = abs_diff / abs(expected_tot) if expected_tot != 0 else 0.0

            is_match = (abs_diff <= self.config.absolute_tolerance) or (rel_diff <= self.config.relative_tolerance)
            status = ReconciliationStatus.PASS.value if is_match else ReconciliationStatus.WARNING.value
            severity = ReconciliationSeverity.INFO.value if is_match else ReconciliationSeverity.WARNING.value

            msg = (
                f"Table I row sum for {state} ({row_sum:,.2f} Cr) numerically agrees with "
                f"Inward ({inward_tot:,.2f} Cr) + Internal ({internal_tot:,.2f} Cr) within tolerance."
                if is_match else
                f"Discrepancy for {state}: Table I row sum ({row_sum:,.2f} Cr) differs from "
                f"Inward + Internal ({expected_tot:,.2f} Cr) by {abs_diff:,.6f} Cr."
            )

            results.append(ReconciliationResult(
                run_id=run_id,
                rule_code="REC-DO05",
                rule_category="DATA-OBSERVED",
                source_tables="Tab I_Stat_to_Stat_Revised_Road, Tab IV_Inward_Revised_Road, Tab V_Internal_Revised_Road",
                dimension="STATE_ROW_MARGINAL",
                entity=state,
                expected_value=expected_tot,
                observed_value=row_sum,
                absolute_difference=abs_diff,
                relative_difference=rel_diff,
                absolute_tolerance=self.config.absolute_tolerance,
                relative_tolerance=self.config.relative_tolerance,
                status=status,
                severity=severity,
                message=msg
            ))

        return results

    # =========================================================================
    # REC-DO06: Table I diagonal vs Table V internal (Special handling)
    # =========================================================================
    def reconcile_rec_do06(
        self,
        raw_data: Dict[str, Any],
        normalized_tables: Dict[str, pd.DataFrame],
        run_id: str
    ) -> List[ReconciliationResult]:
        """
        REC-DO06: Table I diagonal vs Table V internal total across all 33 jurisdictions.
        Holds for 32 jurisdictions; diverges for OTHER TERRITORY.
        Special Governance Rule:
        - For 32 jurisdictions: PASS if within tolerance.
        - For OTHER TERRITORY: Returns status UNRESOLVED (not FAIL), with message:
          'UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION'
          Does not speculate about the cause, rebalance values, or modify either source value.
        """
        results = []
        df_sm = normalized_tables["state_movement"]
        df_scint = normalized_tables["state_chapter_internal"]

        for state in self.config.expected_states:
            # Table I diagonal cell for state
            diag_series = df_sm[(df_sm["origin_state"] == state) & (df_sm["destination_state"] == state)]["movement_value_inr_crore"]
            diag_val = float(diag_series.fillna(0.0).iloc[0]) if not diag_series.empty else 0.0

            # Table V internal total for state
            internal_tot = float(df_scint[df_scint["state"] == state]["movement_value_inr_crore"].fillna(0.0).sum())

            expected_val = internal_tot
            observed_val = diag_val
            abs_diff = abs(observed_val - expected_val)
            rel_diff = abs_diff / abs(expected_val) if expected_val != 0 else 0.0

            if state == "OTHER TERRITORY":
                # Special handling for OTHER TERRITORY: UNRESOLVED status, non-blocking
                results.append(ReconciliationResult(
                    run_id=run_id,
                    rule_code="REC-DO06",
                    rule_category="DATA-OBSERVED",
                    source_tables="Tab I_Stat_to_Stat_Revised_Road, Tab V_Internal_Revised_Road",
                    dimension="DIAGONAL_VS_INTERNAL",
                    entity="OTHER TERRITORY",
                    expected_value=expected_val,
                    observed_value=observed_val,
                    absolute_difference=abs_diff,
                    relative_difference=rel_diff,
                    absolute_tolerance=self.config.absolute_tolerance,
                    relative_tolerance=self.config.relative_tolerance,
                    status=ReconciliationStatus.UNRESOLVED.value,
                    severity=ReconciliationSeverity.WARNING.value,
                    message="UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION"
                ))
            else:
                is_match = (abs_diff <= self.config.absolute_tolerance) or (rel_diff <= self.config.relative_tolerance)
                status = ReconciliationStatus.PASS.value if is_match else ReconciliationStatus.WARNING.value
                severity = ReconciliationSeverity.INFO.value if is_match else ReconciliationSeverity.WARNING.value

                msg = (
                    f"Table I diagonal numerically agrees with Table V internal total for {state} within tolerance."
                    if is_match else
                    f"Discrepancy for {state}: Table I diagonal ({observed_val:,.2f} Cr) differs from "
                    f"Table V internal ({expected_val:,.2f} Cr) by {abs_diff:,.6f} Cr."
                )

                results.append(ReconciliationResult(
                    run_id=run_id,
                    rule_code="REC-DO06",
                    rule_category="DATA-OBSERVED",
                    source_tables="Tab I_Stat_to_Stat_Revised_Road, Tab V_Internal_Revised_Road",
                    dimension="DIAGONAL_VS_INTERNAL",
                    entity=state,
                    expected_value=expected_val,
                    observed_value=observed_val,
                    absolute_difference=abs_diff,
                    relative_difference=rel_diff,
                    absolute_tolerance=self.config.absolute_tolerance,
                    relative_tolerance=self.config.relative_tolerance,
                    status=status,
                    severity=severity,
                    message=msg
                ))

        return results
