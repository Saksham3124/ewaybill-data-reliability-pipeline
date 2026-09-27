# Year-over-Year Statistical Analysis Report

**Pipeline Run ID:** `876b1a4b-c9fd-5198-b153-17b6a725305c`  
**Execution Timestamp:** `2026-09-27 19:21:13 UTC`  
**Reference Snapshot (Historical Baseline):** FY 2022–23 (`data/Road_EwayBill_2022_23.xlsx`)  
**Comparison Snapshot (Production):** FY 2023–24 (`data/Road_EwayBill_2023_24.xlsx`)  
**Framework:** Phase 6 Year-over-Year Statistical Analysis Engine  

---

## 1. Executive Summary & Epistemic Boundaries

> [!IMPORTANT]
> **EPISTEMIC BOUNDARY & DATA QUALITY NOTICE:**  
> This analysis evaluates changes between two discrete annual snapshots (FY 2022–23 vs. FY 2023–24). 
> It is **NOT** a continuous drift monitoring framework. 
> A finding of statistical significance (**`STATISTICALLY_DIFFERENT`**) under the Kolmogorov-Smirnov (KS) 
> or Population Stability Index (PSI) tests indicates that the observed empirical distributions differ under 
> test assumptions. It **must NOT** be interpreted as data-quality failure, corruption, or pipeline breakdown.

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Statistical Tests & Metrics** | **204** | 100.0% |
| **Kolmogorov-Smirnov (KS) Two-Sample Tests** | **7** | 3.4% |
| **Population Stability Index (PSI) Tests** | **7** | 3.4% |
| **Year-over-Year Unit Change Metrics** | **189** | 92.6% |
| **Cross-Year Audit Observations** | **1** | 0.5% |
| **No Material Statistical Change** | **68** | 33.3% |
| **Statistically Significant Shifts** | **136** | 66.7% |
| **Insufficient Data / Not Applicable** | **0** | 0.0% |

---

## 2. Cross-Year Canonical Normalization Layer

To ensure robust comparability without mutating source data, the pipeline applies an explicit canonical normalization layer:

| Historical Source Label (2022–23) | Production Source Label (2023–24) | Unified Canonical Entity | Normalization Rationale |
| :--- | :--- | :--- | :--- |
| `CHHATTISGARH` | `CHATTISGARH` | `CHATTISGARH` | Standardizes double 'H' spelling variation |
| `JAMMU AND KASHMIR` | `JAMMU & KASHMIR` | `JAMMU & KASHMIR` | Standardizes word 'AND' vs ampersand '&' |
| `Other Territory` (Tab V) | `OTHER TERRITORY` | `OTHER TERRITORY` | Standardizes Title Case in historical Table V |

**Table III Summary Handling:** While FY 2022–23 contains summary Column AK (`VALUE (in INR Crore)`), FY 2023–24 does not. In accordance with governance constraints, Column AK is excluded from cross-year comparisons; comparable outward totals are recalculated directly from the 33 state entity columns.

---

## 3. Kolmogorov-Smirnov (KS) Two-Sample Test Results

The two-sample KS test compares empirical cumulative distribution functions (eCDFs) between FY 2022–23 and FY 2023–24 at significance level $\alpha = 0.05$:

| Analytical Dimension | Sample Ref ($N_{22}$) | Sample Comp ($N_{24}$) | KS Statistic ($D$) | p-value | Alpha ($\alpha$) | Statistical Status | Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `STATE_OUTWARD` | 33 | 33 | 0.1818 | 6.5434e-01 | 0.05 | `NO_MATERIAL_STATISTICAL_CHANGE` | No statistically significant difference in empirical distributions under two-sample KS test at alpha = 0.05 (statistic = 0.1818, p-value = 0.6543). |
| `STATE_INWARD` | 33 | 33 | 0.1818 | 6.5434e-01 | 0.05 | `NO_MATERIAL_STATISTICAL_CHANGE` | No statistically significant difference in empirical distributions under two-sample KS test at alpha = 0.05 (statistic = 0.1818, p-value = 0.6543). |
| `STATE_INTERNAL` | 33 | 33 | 0.1818 | 6.5434e-01 | 0.05 | `NO_MATERIAL_STATISTICAL_CHANGE` | No statistically significant difference in empirical distributions under two-sample KS test at alpha = 0.05 (statistic = 0.1818, p-value = 0.6543). |
| `CHAPTER_NATIONAL` | 90 | 90 | 0.1889 | 8.0517e-02 | 0.05 | `NO_MATERIAL_STATISTICAL_CHANGE` | No statistically significant difference in empirical distributions under two-sample KS test at alpha = 0.05 (statistic = 0.1889, p-value = 0.0805). |
| `STATE_CHAPTER_OUTWARD` | 2905 | 2862 | 0.0404 | 1.7390e-02 | 0.05 | `STATISTICALLY_DIFFERENT` | Observed distributions differ under two-sample KS test at alpha = 0.05 (statistic = 0.0404, p-value = 1.74e-02). This indicates a distributional shift between FY 2022–23 and FY 2023–24, but does NOT indicate data corruption or pipeline failure. |
| `STATE_CHAPTER_INWARD` | 2954 | 2943 | 0.0683 | 1.9800e-06 | 0.05 | `STATISTICALLY_DIFFERENT` | Observed distributions differ under two-sample KS test at alpha = 0.05 (statistic = 0.0683, p-value = 1.98e-06). This indicates a distributional shift between FY 2022–23 and FY 2023–24, but does NOT indicate data corruption or pipeline failure. |
| `STATE_CHAPTER_INTERNAL` | 2862 | 2806 | 0.0391 | 2.5363e-02 | 0.05 | `STATISTICALLY_DIFFERENT` | Observed distributions differ under two-sample KS test at alpha = 0.05 (statistic = 0.0391, p-value = 2.54e-02). This indicates a distributional shift between FY 2022–23 and FY 2023–24, but does NOT indicate data corruption or pipeline failure. |

---

## 4. Population Stability Index (PSI) Results

PSI quantifies the shift in distribution proportions using quantile binning derived from the FY 2022–23 reference baseline:

> [!NOTE]
> Thresholds are designated as **`PROJECT CONFIGURATION / INTERPRETATION GUIDANCE`**:  
> - $PSI < 0.10$: No material statistical shift.  
> - $0.10 \le PSI < 0.25$: Moderate statistical shift.  
> - $PSI \ge 0.25$: Significant distributional shift.

| Analytical Dimension | Reference ($N_{22}$) | Comparison ($N_{24}$) | PSI Value | Threshold | Statistical Status | Methodological Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `STATE_OUTWARD` | 33 | 33 | 0.2341 | 0.25 | `STATISTICALLY_DIFFERENT` | PSI = 0.2341 indicates moderate shift (>= 0.10, < 0.25) [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. |
| `STATE_INWARD` | 33 | 33 | 0.3482 | 0.25 | `STATISTICALLY_DIFFERENT` | PSI = 0.3482 >= threshold 0.25 [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. Indicates substantial distributional shift between FY 2022–23 and FY 2023–24. |
| `STATE_INTERNAL` | 33 | 33 | 0.1459 | 0.25 | `STATISTICALLY_DIFFERENT` | PSI = 0.1459 indicates moderate shift (>= 0.10, < 0.25) [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. |
| `CHAPTER_NATIONAL` | 90 | 90 | 0.2697 | 0.25 | `STATISTICALLY_DIFFERENT` | PSI = 0.2697 >= threshold 0.25 [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. Indicates substantial distributional shift between FY 2022–23 and FY 2023–24. |
| `STATE_CHAPTER_OUTWARD` | 2905 | 2862 | 0.0134 | 0.25 | `NO_MATERIAL_STATISTICAL_CHANGE` | PSI = 0.0134 < 0.10 [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. Indicates no material shift in distribution. |
| `STATE_CHAPTER_INWARD` | 2954 | 2943 | 0.0334 | 0.25 | `NO_MATERIAL_STATISTICAL_CHANGE` | PSI = 0.0334 < 0.10 [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. Indicates no material shift in distribution. |
| `STATE_CHAPTER_INTERNAL` | 2862 | 2806 | 0.0114 | 0.25 | `NO_MATERIAL_STATISTICAL_CHANGE` | PSI = 0.0114 < 0.10 [PROJECT CONFIGURATION / INTERPRETATION GUIDANCE]. Indicates no material shift in distribution. |

---

## 5. State-Level Year-over-Year Summary (Aggregate Marginals)

Summary of macro-level aggregate shifts across the 33 jurisdictions:

| Movement Dimension | FY 2022–23 Aggregate (Cr) | FY 2023–24 Aggregate (Cr) | Absolute Change (Cr) | Percentage Change | Overall Distributional Stability |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **State Outward Dispatches** | 62,999,856.01 | 10,429,324.40 | -52,570,531.60 | -83.45% | KS p = 0.6543 (Stable eCDF shape, lower absolute volume) |
| **State Inward Receipts** | 62,999,856.01 | 10,429,324.40 | -52,570,531.60 | -83.45% | KS p = 0.6543 (Stable eCDF shape, lower absolute volume) |
| **State Internal Intra-State** | 31,353,408.74 | 9,890,462.58 | -21,462,946.17 | -68.45% | KS p = 0.6543 (Stable eCDF shape, lower absolute volume) |
| **National Total Movement** | 94,353,264.75 | 20,319,786.98 | -74,033,477.77 | -78.46% | KS p = 0.0805 (Stable eCDF shape at alpha = 0.05) |

---

## 6. Significant Distributional Differences & Context

1. **Magnitude Difference Across Annual Snapshots:** FY 2022–23 and FY 2023–24 have substantially different aggregate magnitudes, while the two-sample KS test evaluates empirical distributional shape ($p = 0.6543 > 0.05$ across state outward, inward, and internal distributions). The data does not imply a causal explanation for the magnitude difference.
2. **State×Chapter Matrix Distributional Sensitivity & Limitation:** For state $\times$ chapter matrices ($N=2,970$), the two-sample KS test flags statistically significant differences ($p < 0.05$). State×chapter cells share common state and chapter aggregates and are therefore structurally dependent. KS results on these flattened matrices are treated as descriptive distributional signals rather than independent-population inference. Statistical significance does NOT imply data corruption or pipeline failure.

---

## 7. Insufficient / Not-Applicable Comparisons

- **Zero-Denominator Protection:** The zero-denominator protection rule is implemented, but no evaluated comparison produced a NOT_APPLICABLE result in this run. For any cells or routes where FY 2022–23 records zero movement ($0.0$ or NULL), the pipeline strictly suppresses percentage change calculation rather than manufacturing synthetic infinities, returning `NOT_APPLICABLE: ZERO_DENOMINATOR`.
- **Sparsity Expansion:** Non-occurring movements (NULLs) expanded slightly from 191 cells in FY 2022–23 to 304 cells in FY 2023–24, reflecting increased route sparsity.

---

## 8. OTHER TERRITORY Cross-Year Historical Observation

> [!WARNING]
> **CROSS-YEAR ANOMALY OBSERVATION:**  
> OTHER TERRITORY diagonal/internal equivalence observed in FY2022–23 (Table I = 333,390.86 Cr, Table V = 333,390.86 Cr, diff = 0.00000000 Cr) but NOT in FY2023–24 (Table I = 258,324.42 Cr, Table V = 181,709.49 Cr, diff = ₹76,614.933539 Cr). The discrepancy is specific to FY 2023–24; cause is not asserted.

### Key Analytical Insights:
1. **Equivalence in FY 2022–23:** In the historical baseline, Table I diagonal (`₹333,390.86` Cr) and Table V internal (`₹333,390.86` Cr) strictly agree (difference $< 10^{-9}$ Cr).
2. **Isolation to FY 2023–24:** The divergence of `+₹76,614.933539` Crore is **an isolated phenomenon occurring only in FY 2023–24**.
3. **Non-Attribution Rule:** The issuing authority provides no methodological notes explaining this divergence. The pipeline preserves both numbers as published and refrains from speculative attribution.

---

## 9. Limitations & Analytical Disclaimers

- **No Causal Inference:** Statistical differences between FY 2022–23 and FY 2023–24 describe empirical variance; they do not establish economic or administrative causation.
- **Structural Dependence:** State×chapter cells share common state and chapter aggregates and are therefore structurally dependent. KS results on these flattened matrices are treated as descriptive distributional signals rather than independent-population inference.
- **No Composite Quality Score:** The platform does not produce a singular 'data quality index' or rank jurisdictions by reliability.
- **Annual Snapshot Granularity:** Comparisons reflect annual aggregations. Sub-annual variations, seasonal cycles, or regulatory policy changes are not observed in this data.
