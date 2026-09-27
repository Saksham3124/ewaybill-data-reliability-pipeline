"""
src/corruption/runner.py
------------------------
Execution harness for Phase 7 Controlled Corruption Simulation and Detection Testing.
Executes all 7 scenarios against clean data copies, evaluates detection capabilities,
and captures structured detection results.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

from src.corruption.models import DetectionResult
from src.corruption.scenarios import (
    get_scenario_definitions,
    apply_scenario_a,
    apply_scenario_b,
    apply_scenario_c,
    apply_scenario_d,
    apply_scenario_e,
    apply_scenario_f,
    apply_scenario_g,
)
from src.validation.engine import ValidationEngine
from src.reconciliation.engine import ReconciliationEngine
from src.statistics.engine import StatisticalAnalysisEngine
from src.statistics.models import StatisticalStatus


class CorruptionSimulationRunner:
    """Executes controlled corruption scenarios and verifies pipeline detection behavior."""

    def __init__(
        self,
        val_engine: Optional[ValidationEngine] = None,
        rec_engine: Optional[ReconciliationEngine] = None,
        stat_engine: Optional[StatisticalAnalysisEngine] = None
    ):
        self.val_engine = val_engine or ValidationEngine()
        self.rec_engine = rec_engine or ReconciliationEngine()
        self.stat_engine = stat_engine or StatisticalAnalysisEngine()
        self.scenario_defs = get_scenario_definitions()

    def run_scenario_a(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario A: Missing State/Chapter Combination."""
        sc = self.scenario_defs["CORRUPT-A"]
        raw_c, norm_c = apply_scenario_a(clean_raw, clean_norm)

        val_results = self.val_engine.validate_completeness(raw_c, norm_c)
        cmp_03 = next((r for r in val_results if r.check_id == "CMP-03"), None)

        detected = cmp_03 is not None and cmp_03.status == "FAIL"
        pipeline_blocked = detected  # Severity is CRITICAL

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector="CMP-03 (Completeness Validation)" if detected else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"CMP-03 caught missing record: expected {cmp_03.expected} records, "
                f"observed {cmp_03.observed} records (difference={cmp_03.difference})."
            ) if detected else "Failed to detect missing record in state_chapter_outward.",
            evidence_details={"check_id": "CMP-03", "observed": cmp_03.observed if cmp_03 else None}
        )

    def run_scenario_b(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario B: Duplicate Logical Record."""
        sc = self.scenario_defs["CORRUPT-B"]
        raw_c, norm_c = apply_scenario_b(clean_raw, clean_norm)

        val_results = self.val_engine.validate_uniqueness(norm_c)
        unq_03 = next((r for r in val_results if r.check_id == "UNQ-03"), None)

        detected = unq_03 is not None and unq_03.status == "FAIL"
        pipeline_blocked = detected  # Severity is CRITICAL

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector="UNQ-03 (Uniqueness Validation)" if detected else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"UNQ-03 caught duplicate logical record: expected {unq_03.expected}, "
                f"observed {unq_03.observed} (difference={unq_03.difference})."
            ) if detected else "Failed to detect duplicate record in state_chapter_outward.",
            evidence_details={"check_id": "UNQ-03", "observed": unq_03.observed if unq_03 else None}
        )

    def run_scenario_c(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario C: Invalid Chapter Code."""
        sc = self.scenario_defs["CORRUPT-C"]
        raw_c, norm_c = apply_scenario_c(clean_raw, clean_norm)

        val_results = self.val_engine.validate_domain(norm_c)
        dom_03 = next((r for r in val_results if r.check_id == "DOM-03-chapter_movement"), None)

        detected = dom_03 is not None and dom_03.status == "FAIL"
        pipeline_blocked = detected  # Severity is ERROR

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector="DOM-03-chapter_movement (Domain Validation)" if detected else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"DOM-03 caught invalid chapter code: {dom_03.observed} "
                f"(difference={dom_03.difference})."
            ) if detected else "Failed to detect invalid chapter code in chapter_movement.",
            evidence_details={"check_id": "DOM-03-chapter_movement", "observed": dom_03.observed if dom_03 else None}
        )

    def run_scenario_d(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario D: Altered Movement Value without Totals Update."""
        sc = self.scenario_defs["CORRUPT-D"]
        raw_c, norm_c = apply_scenario_d(clean_raw, clean_norm)

        tot_results = self.val_engine.validate_source_totals(raw_c)
        rec_v02 = next((r for r in tot_results if r.check_id == "REC-V02"), None)

        rec_results = self.rec_engine.run_all_reconciliations(raw_c, norm_c)
        rec_do02 = next((r for r in rec_results if r.rule_code == "REC-DO02"), None)
        rec_do05 = next((r for r in rec_results if r.rule_code == "REC-DO05" and r.entity == "MAHARASHTRA"), None)

        detected_tot = rec_v02 is not None and rec_v02.status == "FAIL"
        detected_rec = (rec_do02 is not None and rec_do02.status in ("WARNING", "FAIL")) or (
            rec_do05 is not None and rec_do05.status in ("WARNING", "FAIL")
        )
        detected = detected_tot or detected_rec
        # REC-V02 is a source-total validation check in ValidationEngine; its failure blocks trusted loading
        pipeline_blocked = detected_tot

        actual_detectors = []
        if detected_tot:
            actual_detectors.append("REC-V02 (Source-Total Validation)")
        if detected_rec:
            actual_detectors.append("REC-DO02/REC-DO05 (Reconciliation)")

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector=" & ".join(actual_detectors) if actual_detectors else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"REC-V02 caught column sum deviation of {rec_v02.difference:.2f} Cr in MAHARASHTRA; "
                f"REC-DO02 caught outward/inward cross-table discrepancy of {rec_do02.absolute_difference:.2f} Cr."
            ) if detected else "Failed to detect altered movement value.",
            evidence_details={
                "rec_v02_diff": rec_v02.difference if rec_v02 else None,
                "rec_do02_diff": rec_do02.absolute_difference if rec_do02 else None
            }
        )

    def run_scenario_e(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario E: Missing State Entity Column from One Table."""
        sc = self.scenario_defs["CORRUPT-E"]
        raw_c, norm_c = apply_scenario_e(clean_raw, clean_norm)

        val_results = self.val_engine.validate_completeness(raw_c, norm_c)
        cmp_03 = next((r for r in val_results if r.check_id == "CMP-03"), None)

        rec_results = self.rec_engine.run_all_reconciliations(raw_c, norm_c)
        rec_do02 = next((r for r in rec_results if r.rule_code == "REC-DO02"), None)

        detected_cmp = cmp_03 is not None and cmp_03.status == "FAIL"
        detected_rec = rec_do02 is not None and rec_do02.status in ("WARNING", "FAIL")
        detected = detected_cmp or detected_rec
        pipeline_blocked = detected_cmp

        actual_detectors = []
        if detected_cmp:
            actual_detectors.append("CMP-03 (Completeness Validation)")
        if detected_rec:
            actual_detectors.append("REC-DO02 (Reconciliation)")

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector=" & ".join(actual_detectors) if actual_detectors else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"CMP-03 caught missing BIHAR state records: expected {cmp_03.expected}, "
                f"observed {cmp_03.observed} (difference={cmp_03.difference} records); "
                f"REC-DO02 flagged cross-table imbalance of {rec_do02.absolute_difference:,.2f} Cr."
            ) if detected else "Failed to detect missing state column BIHAR.",
            evidence_details={"missing_records": cmp_03.difference if cmp_03 else None}
        )

    def run_scenario_f(
        self,
        clean_raw: Dict[str, Any],
        clean_norm: Dict[str, pd.DataFrame]
    ) -> DetectionResult:
        """Scenario F: Numeric-to-Text Corruption."""
        sc = self.scenario_defs["CORRUPT-F"]
        raw_c, norm_c = apply_scenario_f(clean_raw, clean_norm)

        val_results = self.val_engine.validate_numeric(norm_c)
        num_01 = next((r for r in val_results if r.check_id == "NUM-01-state_chapter_internal"), None)

        detected = num_01 is not None and num_01.status == "FAIL"
        pipeline_blocked = detected  # Severity is ERROR

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector="NUM-01-state_chapter_internal (Numeric Validation)" if detected else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"NUM-01 caught non-numeric movement value: observed {num_01.observed} "
                f"(affected_records={num_01.affected_records})."
            ) if detected else "Failed to detect non-numeric string in state_chapter_internal.",
            evidence_details={"non_numeric_count": num_01.affected_records if num_01 else None}
        )

    def run_scenario_g(
        self,
        clean_raw_22: Dict[str, Any],
        clean_raw_24: Dict[str, Any]
    ) -> DetectionResult:
        """Scenario G: Controlled Distribution Shift (Statistical Signal Detection)."""
        sc = self.scenario_defs["CORRUPT-G"]
        raw_22_c, raw_24_c = apply_scenario_g(clean_raw_22, clean_raw_24)

        dims = self.stat_engine.extract_comparable_dimensions(raw_22_c, raw_24_c)
        df_so = dims["state_outward"]
        s_ref = df_so["val_2022_23"].dropna().values.astype(float)
        s_comp = df_so["val_2023_24"].dropna().values.astype(float)

        ks_res = self.stat_engine.run_ks_test(s_ref, s_comp, "STATE_OUTWARD", "TEST_DIST", "run_corrupt_g")
        psi_res = self.stat_engine.run_psi_test(s_ref, s_comp, "STATE_OUTWARD", "TEST_STAB", "run_corrupt_g", num_bins=5)

        detected_ks = ks_res.status == StatisticalStatus.STATISTICALLY_DIFFERENT.value
        detected_psi = psi_res.status == StatisticalStatus.STATISTICALLY_DIFFERENT.value
        detected = detected_ks or detected_psi

        # Statistical detection is an advisory signal and does NOT imply pipeline failure
        pipeline_blocked = False

        actual_detectors = []
        if detected_ks:
            actual_detectors.append("KS_TEST")
        if detected_psi:
            actual_detectors.append("PSI")

        return DetectionResult(
            scenario_id=sc.scenario_id,
            corruption_type=sc.corruption_type,
            expected_detector=sc.expected_detector,
            actual_detector=f"{' & '.join(actual_detectors)} (Statistical Analysis Engine)" if actual_detectors else None,
            detected=detected,
            pipeline_blocked=pipeline_blocked,
            false_positive=False,
            affected_table=sc.source_table,
            affected_field=sc.target_field,
            affected_record=sc.target_record,
            original_value=sc.original_value,
            corrupted_value=sc.corrupted_value,
            detection_message=(
                f"Statistical engine detected controlled shift: KS statistic={ks_res.statistic:.4f}, "
                f"p-value={ks_res.p_value:.2e} (< 0.05); PSI={psi_res.psi_value:.4f} (>= 0.25 threshold). "
                "Triggered STATISTICALLY_DIFFERENT advisory signal without blocking trusted loading."
            ) if detected else "Failed to detect controlled distribution shift.",
            evidence_details={
                "ks_statistic": ks_res.statistic,
                "ks_p_value": ks_res.p_value,
                "psi_value": psi_res.psi_value
            }
        )

    def run_all_scenarios(
        self,
        clean_raw_22: Dict[str, Any],
        clean_raw_24: Dict[str, Any],
        clean_norm_24: Dict[str, pd.DataFrame]
    ) -> List[DetectionResult]:
        """Runs all 7 controlled corruption simulation scenarios."""
        results: List[DetectionResult] = []
        results.append(self.run_scenario_a(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_b(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_c(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_d(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_e(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_f(clean_raw_24, clean_norm_24))
        results.append(self.run_scenario_g(clean_raw_22, clean_raw_24))
        return results
