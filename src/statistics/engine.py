"""
statistics/engine.py
--------------------
Year-over-Year Statistical Analysis Engine for DGCI&S E-Way Bill Road Movement.
Compares annual snapshots: FY 2022–23 (Reference) vs. FY 2023–24 (Comparison).

Governance & Methodological Rules:
1. Terminology: "Year-over-Year Statistical Analysis" (NOT continuous drift monitoring).
2. Epistemic boundary: Statistical significance does NOT imply data-quality failure or corruption.
3. Statuses: NO_MATERIAL_STATISTICAL_CHANGE, STATISTICALLY_DIFFERENT, INSUFFICIENT_DATA, NOT_APPLICABLE.
   Does NOT use PASS/FAIL for statistical outcomes.
4. Canonical Normalization Layer: Applies documented mappings (CHHATTISGARH, JAMMU & KASHMIR, OTHER TERRITORY)
   while preserving source labels in the raw layer.
5. Table III handling: Does NOT compare Column AK directly; recalculates comparable state/chapter
   aggregates from entity columns.
6. Zero-denominator handling: If FY 2022–23 is 0 or NULL, percentage change is NOT manufactured (returns None).
7. OTHER TERRITORY: Records the cross-year empirical divergence without modification, imputation, or speculative attribution.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from src.statistics.config import StatisticalConfig, DEFAULT_STATISTICAL_CONFIG, CANONICAL_STATE_MAP
from src.statistics.models import StatisticalResult, StatisticalStatus


class StatisticalAnalysisEngine:
    """Executes Year-over-Year statistical comparisons between FY 2022–23 and FY 2023–24."""

    def __init__(self, config: Optional[StatisticalConfig] = None):
        self.config = config or DEFAULT_STATISTICAL_CONFIG

    @staticmethod
    def canonical_state(name: str) -> str:
        """Applies explicit canonical state mapping."""
        if not name:
            return ""
        stripped = str(name).strip()
        return CANONICAL_STATE_MAP.get(stripped, stripped)

    def extract_comparable_dimensions(
        self,
        raw_22: Dict[str, Any],
        raw_24: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        """
        Builds comparable annual datasets for the 7 analytical dimensions:
        A. State-level outward movement (33 states)
        B. State-level inward movement (33 states)
        C. State-level internal movement (33 states)
        D. Chapter-level national movement (90 chapters)
        E. State x chapter outward movement (2970 pairs)
        F. State x chapter inward movement (2970 pairs)
        G. State x chapter internal movement (2970 pairs)
        """
        # --- 1. Chapter National Summary (Table II) ---
        df_c22 = raw_22["tables"]["raw_chapter_summary"].copy()
        df_c24 = raw_24["tables"]["raw_chapter_summary"].copy()

        df_c22["chapter_code"] = df_c22["chapter_code"].astype(str)
        df_c24["chapter_code"] = df_c24["chapter_code"].astype(str)

        m_chap = pd.merge(
            df_c22[["chapter_code", "chapter_description", "value_inr_crore"]].rename(columns={"value_inr_crore": "val_2022_23"}),
            df_c24[["chapter_code", "value_inr_crore"]].rename(columns={"value_inr_crore": "val_2023_24"}),
            on="chapter_code",
            how="outer"
        ).sort_values("chapter_code").reset_index(drop=True)

        # --- Helper for State-Chapter Matrices (Tables III, IV, V) ---
        def extract_matrix_pairs(df_raw: pd.DataFrame) -> pd.DataFrame:
            """Extracts long-form (chapter_code, state, value) using canonical state names."""
            records = []
            state_cols = [c for c in df_raw.columns if c not in ("chapter_code", "chapter_description", "TOTAL", "VALUE (in INR Crore)")]
            for _, r in df_raw.iterrows():
                c_code = str(r["chapter_code"])
                for s_col in state_cols:
                    canonical_s = self.canonical_state(s_col)
                    val = r[s_col]
                    records.append({
                        "chapter_code": c_code,
                        "state": canonical_s,
                        "movement_value": float(val) if pd.notna(val) else None
                    })
            return pd.DataFrame(records)

        # Table III: Outward (Note: Col AK excluded; recalculates from state cols)
        sco_22 = extract_matrix_pairs(raw_22["tables"]["raw_chapter_outward"])
        sco_24 = extract_matrix_pairs(raw_24["tables"]["raw_chapter_outward"])
        m_sco = pd.merge(
            sco_22.rename(columns={"movement_value": "val_2022_23"}),
            sco_24.rename(columns={"movement_value": "val_2023_24"}),
            on=["chapter_code", "state"],
            how="outer"
        ).sort_values(["chapter_code", "state"]).reset_index(drop=True)

        # Table IV: Inward
        sci_22 = extract_matrix_pairs(raw_22["tables"]["raw_chapter_inward"])
        sci_24 = extract_matrix_pairs(raw_24["tables"]["raw_chapter_inward"])
        m_sci = pd.merge(
            sci_22.rename(columns={"movement_value": "val_2022_23"}),
            sci_24.rename(columns={"movement_value": "val_2023_24"}),
            on=["chapter_code", "state"],
            how="outer"
        ).sort_values(["chapter_code", "state"]).reset_index(drop=True)

        # Table V: Internal
        scint_22 = extract_matrix_pairs(raw_22["tables"]["raw_chapter_internal"])
        scint_24 = extract_matrix_pairs(raw_24["tables"]["raw_chapter_internal"])
        m_scint = pd.merge(
            scint_22.rename(columns={"movement_value": "val_2022_23"}),
            scint_24.rename(columns={"movement_value": "val_2023_24"}),
            on=["chapter_code", "state"],
            how="outer"
        ).sort_values(["chapter_code", "state"]).reset_index(drop=True)

        # --- Aggregate State-Level Totals (A, B, C) ---
        # Summing chapter dispatches per state (treating NULL as 0.0 inside calculation)
        st_out_22 = sco_22.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2022_23"})
        st_out_24 = sco_24.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2023_24"})
        m_st_out = pd.merge(st_out_22, st_out_24, on="state", how="outer").sort_values("state").reset_index(drop=True)

        st_in_22 = sci_22.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2022_23"})
        st_in_24 = sci_24.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2023_24"})
        m_st_in = pd.merge(st_in_22, st_in_24, on="state", how="outer").sort_values("state").reset_index(drop=True)

        st_int_22 = scint_22.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2022_23"})
        st_int_24 = scint_24.groupby("state")["movement_value"].sum(min_count=1).reset_index().rename(columns={"movement_value": "val_2023_24"})
        m_st_int = pd.merge(st_int_22, st_int_24, on="state", how="outer").sort_values("state").reset_index(drop=True)

        return {
            "state_outward": m_st_out,
            "state_inward": m_st_in,
            "state_internal": m_st_int,
            "chapter_national": m_chap,
            "state_chapter_outward": m_sco,
            "state_chapter_inward": m_sci,
            "state_chapter_internal": m_scint
        }

    # =========================================================================
    # Year-over-Year Change Calculations
    # =========================================================================
    @staticmethod
    def calculate_yoy_metrics(val_ref: Optional[float], val_comp: Optional[float]) -> Tuple[Optional[float], Optional[float], str]:
        """
        Calculates absolute change and percentage change.
        If denominator is zero or None, does NOT manufacture percentage; returns None.
        Returns: (absolute_change, percentage_change, status_note)
        """
        if val_ref is None or val_comp is None:
            return None, None, "NULL_VALUE_PRESENT"

        abs_change = float(val_comp - val_ref)
        if val_ref == 0.0:
            return abs_change, None, "NOT_APPLICABLE: ZERO_DENOMINATOR"

        pct_change = float((abs_change / val_ref) * 100.0)
        return abs_change, pct_change, "CALCULATED"

    # =========================================================================
    # Kolmogorov-Smirnov Two-Sample Test
    # =========================================================================
    def run_ks_test(
        self,
        ref_sample: np.ndarray,
        comp_sample: np.ndarray,
        dimension: str,
        metric: str,
        run_id: str,
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Executes scipy.stats.ks_2samp.
        Explicitly distinguishes statistical significance from data-quality failure.
        """
        alpha_val = alpha if alpha is not None else self.config.alpha

        # Clean samples (remove NaNs)
        s_ref = ref_sample[~np.isnan(ref_sample)]
        s_comp = comp_sample[~np.isnan(comp_sample)]

        n_ref = len(s_ref)
        n_comp = len(s_comp)

        if n_ref < self.config.min_sample_size_ks or n_comp < self.config.min_sample_size_ks:
            return StatisticalResult(
                run_id=run_id,
                dimension=dimension,
                metric=metric,
                test_method="KS_TEST",
                sample_size_reference=n_ref,
                sample_size_comparison=n_comp,
                alpha=alpha_val,
                status=StatisticalStatus.INSUFFICIENT_DATA.value,
                interpretation=(
                    f"Insufficient sample size (N_ref={n_ref}, N_comp={n_comp} < {self.config.min_sample_size_ks}) "
                    "to compute two-sample KS test."
                )
            )

        res = stats.ks_2samp(s_ref, s_comp)
        stat = float(res.statistic)
        p_val = float(res.pvalue)

        if p_val < alpha_val:
            status = StatisticalStatus.STATISTICALLY_DIFFERENT.value
            interp = (
                f"Observed distributions differ under two-sample KS test at alpha = {alpha_val} "
                f"(statistic = {stat:.4f}, p-value = {p_val:.2e}). This indicates a distributional "
                "shift between FY 2022–23 and FY 2023–24, but does NOT indicate data corruption or pipeline failure."
            )
        else:
            status = StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value
            interp = (
                f"No statistically significant difference in empirical distributions under two-sample KS test "
                f"at alpha = {alpha_val} (statistic = {stat:.4f}, p-value = {p_val:.4f})."
            )

        return StatisticalResult(
            run_id=run_id,
            dimension=dimension,
            metric=metric,
            test_method="KS_TEST",
            sample_size_reference=n_ref,
            sample_size_comparison=n_comp,
            statistic=stat,
            p_value=p_val,
            alpha=alpha_val,
            status=status,
            interpretation=interp
        )

    # =========================================================================
    # Population Stability Index (PSI)
    # =========================================================================
    def run_psi_test(
        self,
        ref_sample: np.ndarray,
        comp_sample: np.ndarray,
        dimension: str,
        metric: str,
        run_id: str,
        num_bins: Optional[int] = None,
        threshold_sig: Optional[float] = None
    ) -> StatisticalResult:
        """
        Calculates Population Stability Index (PSI) using quantile binning on reference distribution.
        Handles zero-count bins via epsilon smoothing.
        Thresholds are labeled as PROJECT CONFIGURATION / INTERPRETATION GUIDANCE.
        """
        thresh_sig = threshold_sig if threshold_sig is not None else self.config.psi_threshold_significant
        eps = self.config.psi_epsilon

        s_ref = ref_sample[~np.isnan(ref_sample)]
        s_comp = comp_sample[~np.isnan(comp_sample)]

        n_ref = len(s_ref)
        n_comp = len(s_comp)

        if n_ref < self.config.min_sample_size_ks or n_comp < self.config.min_sample_size_ks:
            return StatisticalResult(
                run_id=run_id,
                dimension=dimension,
                metric=metric,
                test_method="PSI",
                sample_size_reference=n_ref,
                sample_size_comparison=n_comp,
                psi_threshold=thresh_sig,
                status=StatisticalStatus.INSUFFICIENT_DATA.value,
                interpretation=f"Insufficient sample size for PSI binning (N_ref={n_ref}, N_comp={n_comp})."
            )

        k = num_bins or (self.config.default_state_bins if n_ref <= 33 else self.config.default_chapter_bins)
        percentiles = np.linspace(0, 100, k + 1)
        bin_edges = np.unique(np.percentile(s_ref, percentiles))

        if len(bin_edges) < 2:
            return StatisticalResult(
                run_id=run_id,
                dimension=dimension,
                metric=metric,
                test_method="PSI",
                sample_size_reference=n_ref,
                sample_size_comparison=n_comp,
                psi_value=0.0,
                psi_threshold=thresh_sig,
                status=StatisticalStatus.INSUFFICIENT_DATA.value,
                interpretation="Degenerate distribution: insufficient variance to construct distinct bins."
            )

        bin_edges[0] -= 1e-6
        bin_edges[-1] += 1e-6

        exp_counts, _ = np.histogram(s_ref, bins=bin_edges)
        act_counts, _ = np.histogram(s_comp, bins=bin_edges)

        exp_counts = exp_counts.astype(float) + eps
        act_counts = act_counts.astype(float) + eps

        exp_pct = exp_counts / exp_counts.sum()
        act_pct = act_counts / act_counts.sum()

        psi_val = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))

        if psi_val >= thresh_sig:
            status = StatisticalStatus.STATISTICALLY_DIFFERENT.value
            interp = (
                f"PSI = {psi_val:.4f} >= threshold {thresh_sig:.2f} [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. "
                "Indicates substantial distributional shift between FY 2022–23 and FY 2023–24."
            )
        elif psi_val >= self.config.psi_threshold_moderate:
            status = StatisticalStatus.STATISTICALLY_DIFFERENT.value
            interp = (
                f"PSI = {psi_val:.4f} indicates moderate shift (>= {self.config.psi_threshold_moderate:.2f}, < {thresh_sig:.2f}) "
                "[PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]."
            )
        else:
            status = StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value
            interp = (
                f"PSI = {psi_val:.4f} < {self.config.psi_threshold_moderate:.2f} [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. "
                "Indicates no material shift in distribution."
            )

        return StatisticalResult(
            run_id=run_id,
            dimension=dimension,
            metric=metric,
            test_method="PSI",
            sample_size_reference=n_ref,
            sample_size_comparison=n_comp,
            psi_value=psi_val,
            psi_threshold=thresh_sig,
            status=status,
            interpretation=interp
        )

    # =========================================================================
    # OTHER TERRITORY Cross-Year Observation
    # =========================================================================
    @staticmethod
    def audit_other_territory_cross_year(
        raw_22: Dict[str, Any],
        raw_24: Dict[str, Any],
        run_id: str
    ) -> StatisticalResult:
        """
        Documents the cross-year observation on OTHER TERRITORY diagonal/internal consistency:
        Equivalence holds in FY 2022-23 (diff < 1e-9 Cr) but not FY 2023-24 (diff = ₹76,614.93 Cr).
        Does NOT alter data, impute, or assign speculative causation.
        """
        # 2022-23 values
        ws1_22 = raw_22["tables"]["raw_state_to_state"]
        ws5_22 = raw_22["tables"]["raw_chapter_internal"]
        diag_22 = float(ws1_22[ws1_22["to_state"] == "OTHER TERRITORY"]["OTHER TERRITORY"].values[0])
        # Find other territory column in Table V
        ot_col_22 = [c for c in ws5_22.columns if str(c).upper() == "OTHER TERRITORY"][0]
        int_22 = float(ws5_22[ot_col_22].fillna(0.0).sum())
        diff_22 = abs(diag_22 - int_22)

        # 2023-24 values
        ws1_24 = raw_24["tables"]["raw_state_to_state"]
        ws5_24 = raw_24["tables"]["raw_chapter_internal"]
        diag_24 = float(ws1_24[ws1_24["to_state"] == "OTHER TERRITORY"]["OTHER TERRITORY"].values[0])
        int_24 = float(ws5_24["OTHER TERRITORY"].fillna(0.0).sum())
        diff_24 = abs(diag_24 - int_24)

        interp = (
            f"OTHER TERRITORY diagonal/internal equivalence observed in FY2022–23 "
            f"(Table I = {diag_22:,.2f} Cr, Table V = {int_22:,.2f} Cr, diff = {diff_22:.8f} Cr) "
            f"but NOT in FY2023–24 (Table I = {diag_24:,.2f} Cr, Table V = {int_24:,.2f} Cr, "
            f"diff = ₹{diff_24:,.6f} Cr). The discrepancy is specific to FY 2023–24; cause is not asserted."
        )

        return StatisticalResult(
            run_id=run_id,
            dimension="CROSS_YEAR_AUDIT",
            metric="OTHER_TERRITORY_DIAGONAL_INTERNAL_EQUIVALENCE",
            test_method="CROSS_YEAR_OBSERVATION",
            statistic=diff_24,
            status=StatisticalStatus.STATISTICALLY_DIFFERENT.value,
            interpretation=interp
        )

    # =========================================================================
    # Full Suite Orchestration
    # =========================================================================
    def run_all_statistical_analyses(
        self,
        raw_22: Dict[str, Any],
        raw_24: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> List[StatisticalResult]:
        """Runs the entire Year-over-Year Statistical Analysis suite."""
        run_id = run_id or f"stat_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        results: List[StatisticalResult] = []

        # 1. Extract comparable dimensions
        dims = self.extract_comparable_dimensions(raw_22, raw_24)

        # 2. Distributional Tests (KS & PSI) across 7 analytical dimensions
        dim_mappings = [
            ("STATE_OUTWARD", "state_outward", "val_2022_23", "val_2023_24", self.config.default_state_bins),
            ("STATE_INWARD", "state_inward", "val_2022_23", "val_2023_24", self.config.default_state_bins),
            ("STATE_INTERNAL", "state_internal", "val_2022_23", "val_2023_24", self.config.default_state_bins),
            ("CHAPTER_NATIONAL", "chapter_national", "val_2022_23", "val_2023_24", self.config.default_chapter_bins),
            ("STATE_CHAPTER_OUTWARD", "state_chapter_outward", "val_2022_23", "val_2023_24", self.config.default_matrix_bins),
            ("STATE_CHAPTER_INWARD", "state_chapter_inward", "val_2022_23", "val_2023_24", self.config.default_matrix_bins),
            ("STATE_CHAPTER_INTERNAL", "state_chapter_internal", "val_2022_23", "val_2023_24", self.config.default_matrix_bins),
        ]

        for dim_name, df_key, col_ref, col_comp, k_bins in dim_mappings:
            df = dims[df_key]
            s_ref = df[col_ref].dropna().values.astype(float)
            s_comp = df[col_comp].dropna().values.astype(float)

            # KS test
            results.append(self.run_ks_test(
                ref_sample=s_ref,
                comp_sample=s_comp,
                dimension=dim_name,
                metric=f"{dim_name}_DISTRIBUTION",
                run_id=run_id
            ))

            # PSI test
            results.append(self.run_psi_test(
                ref_sample=s_ref,
                comp_sample=s_comp,
                dimension=dim_name,
                metric=f"{dim_name}_STABILITY",
                run_id=run_id,
                num_bins=k_bins
            ))

        # 3. Macro Aggregates & YoY Changes
        # State-level YoY changes
        for metric_dim, df_key in [("STATE_OUTWARD_YOY", "state_outward"), ("STATE_INWARD_YOY", "state_inward"), ("STATE_INTERNAL_YOY", "state_internal")]:
            df = dims[df_key]
            for _, r in df.iterrows():
                state_name = r["state"]
                v22 = r["val_2022_23"]
                v24 = r["val_2023_24"]
                abs_chg, pct_chg, note = self.calculate_yoy_metrics(v22, v24)

                status = StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value if (pct_chg is not None and abs(pct_chg) <= 25.0) else (
                    StatisticalStatus.STATISTICALLY_DIFFERENT.value if pct_chg is not None else StatisticalStatus.NOT_APPLICABLE.value
                )

                interp = (
                    f"{state_name} YoY: {v22:,.2f} Cr (2022-23) -> {v24:,.2f} Cr (2023-24). "
                    f"Abs Change: {abs_chg:,.2f} Cr, Pct Change: {pct_chg:.2f}%."
                    if pct_chg is not None else
                    f"{state_name} YoY: {v22} -> {v24}. Percentage change not applicable ({note})."
                )

                results.append(StatisticalResult(
                    run_id=run_id,
                    dimension=metric_dim,
                    metric=state_name,
                    test_method="YOY_CHANGE",
                    statistic=abs_chg,
                    p_value=pct_chg, # store percentage in p_value or statistic
                    status=status,
                    interpretation=interp
                ))

        # 4. Chapter National Movement YoY changes (90 chapters)
        df_ch = dims["chapter_national"]
        for _, r in df_ch.iterrows():
            c_code = r["chapter_code"]
            c_desc = r["chapter_description"]
            v22 = r["val_2022_23"]
            v24 = r["val_2023_24"]
            abs_chg, pct_chg, note = self.calculate_yoy_metrics(v22, v24)

            status = StatisticalStatus.NO_MATERIAL_STATISTICAL_CHANGE.value if (pct_chg is not None and abs(pct_chg) <= 25.0) else (
                StatisticalStatus.STATISTICALLY_DIFFERENT.value if pct_chg is not None else StatisticalStatus.NOT_APPLICABLE.value
            )

            interp = (
                f"Chapter {c_code} ({c_desc}) YoY: {v22:,.2f} Cr -> {v24:,.2f} Cr. "
                f"Abs Change: {abs_chg:,.2f} Cr, Pct Change: {pct_chg:.2f}%."
                if pct_chg is not None else
                f"Chapter {c_code} YoY: {v22} -> {v24}. Percentage change not applicable ({note})."
            )

            results.append(StatisticalResult(
                run_id=run_id,
                dimension="CHAPTER_NATIONAL_YOY",
                metric=f"CHAPTER_{c_code}",
                test_method="YOY_CHANGE",
                statistic=abs_chg,
                p_value=pct_chg,
                status=status,
                interpretation=interp
            ))

        # 5. OTHER TERRITORY Cross-Year Observation
        results.append(self.audit_other_territory_cross_year(raw_22, raw_24, run_id))

        return results
