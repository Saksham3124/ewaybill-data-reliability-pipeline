# Controlled Corruption Simulation & Detection Report

**Execution Timestamp:** `2026-09-27 15:50:31 UTC`  
**Simulation Run ID:** `corrupt_sim_20260927_155031`  
**Baseline Source (2022–23):** `data/Road_EwayBill_2022_23.xlsx` (Byte-for-byte unchanged)  
**Production Source (2023–24):** `data/Road_EwayBill_2023_24.xlsx` (Byte-for-byte unchanged)  
**Framework:** Phase 7 Controlled Corruption Simulation Engine  

---

## 1. Executive Summary

> [!IMPORTANT]
> **METHODOLOGICAL PURPOSE & TEST ISOLATION:**  
> The purpose of this simulation is to empirically evaluate the **detection capability** of the existing 
> validation, reconciliation, and statistical analysis engines against controlled, reproducible data defects. 
> All corruptions were executed in isolated in-memory deep copies. Neither original source Excel workbooks 
> nor persistent PostgreSQL production/trusted warehouse tables were mutated or contaminated.

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Scenarios Evaluated** | **7** | 100.0% |
| **Scenarios Successfully Detected** | **7** | 100.0% |
| **Scenarios Missed** | **0** | 0.0% |
| **Pipeline Blocked (Trusted Loading Halted)** | **6** | 85.7% |
| **Advisory / Non-Blocking Detections** | **1** | 14.3% |
| **False Positives** | **0** | 0.0% |

---

## 2. Detection Matrix

| Scenario | Corruption Type | Expected Detector | Actual Detector | Detected? | Pipeline Blocked? | False Positive? |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **CORRUPT-A** | `MISSING_RECORD` | COMPLETENESS_VALIDATION (CMP-03) | CMP-03 (Completeness Validation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-B** | `DUPLICATE_RECORD` | UNIQUENESS_VALIDATION (UNQ-03) | UNQ-03 (Uniqueness Validation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-C** | `INVALID_DOMAIN` | DOMAIN_VALIDATION (DOM-03) | DOM-03-chapter_movement (Domain Validation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-D** | `ALTERED_NUMERIC` | SOURCE_TOTAL_VALIDATION (REC-V02) / RECONCILIATION (REC-DO02, REC-DO05) | REC-V02 (Source-Total Validation) & REC-DO02/REC-DO05 (Reconciliation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-E** | `MISSING_ENTITY_COLUMN` | COMPLETENESS_VALIDATION (CMP-03) / RECONCILIATION | CMP-03 (Completeness Validation) & REC-DO02 (Reconciliation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-F** | `NUMERIC_TO_TEXT` | NUMERIC_VALIDATION (NUM-01) | NUM-01-state_chapter_internal (Numeric Validation) | ✅ YES | 🛑 BLOCKED | NO |
| **CORRUPT-G** | `DISTRIBUTION_SHIFT` | STATISTICAL_ANALYSIS (KS_TEST / PSI) | KS_TEST & PSI (Statistical Analysis Engine) | ✅ YES | ℹ️ ADVISORY | NO |

---

## 3. Scenario Profiles & Detection Evidence

### CORRUPT-A: MISSING_RECORD
- **Target Location:** Table `state_chapter_outward`, Field `(chapter_code, state)`, Record `chapter_code='10', state='MAHARASHTRA'`
- **Original Value:** `Record present (1 row out of 2,970)`
- **Corrupted Value:** `Record removed (2,969 rows remaining)`
- **Expected Detector:** COMPLETENESS_VALIDATION (CMP-03)
- **Actual Detector:** CMP-03 (Completeness Validation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** CMP-03 caught missing record: expected 2970 records, observed 2969 records (difference=1.0).
- **Diagnostic Evidence:** `{'check_id': 'CMP-03', 'observed': 2969}`

### CORRUPT-B: DUPLICATE_RECORD
- **Target Location:** Table `state_chapter_outward`, Field `(chapter_code, state)`, Record `chapter_code='10', state='MAHARASHTRA'`
- **Original Value:** `1 unique record`
- **Corrupted Value:** `2 identical records (duplicate row appended, 2,971 rows total)`
- **Expected Detector:** UNIQUENESS_VALIDATION (UNQ-03)
- **Actual Detector:** UNQ-03 (Uniqueness Validation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** UNQ-03 caught duplicate logical record: expected 0 duplicates, observed 2 duplicates (difference=2.0).
- **Diagnostic Evidence:** `{'check_id': 'UNQ-03', 'observed': '2 duplicates'}`

### CORRUPT-C: INVALID_DOMAIN
- **Target Location:** Table `chapter_movement`, Field `chapter_code`, Record `chapter_code='10'`
- **Original Value:** `'10'`
- **Corrupted Value:** `'999'`
- **Expected Detector:** DOMAIN_VALIDATION (DOM-03)
- **Actual Detector:** DOM-03-chapter_movement (Domain Validation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** DOM-03 caught invalid chapter code: 1 invalid (difference=1.0).
- **Diagnostic Evidence:** `{'check_id': 'DOM-03-chapter_movement', 'observed': '1 invalid'}`

### CORRUPT-D: ALTERED_NUMERIC
- **Target Location:** Table `raw_chapter_outward`, Field `MAHARASHTRA`, Record `chapter_code='10'`
- **Original Value:** `1687.5131552319997`
- **Corrupted Value:** `2187.513155232`
- **Expected Detector:** SOURCE_TOTAL_VALIDATION (REC-V02) / RECONCILIATION (REC-DO02, REC-DO05)
- **Actual Detector:** REC-V02 (Source-Total Validation) & REC-DO02/REC-DO05 (Reconciliation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** REC-V02 caught column sum deviation of 500.00 Cr in MAHARASHTRA; REC-DO02 caught outward/inward cross-table discrepancy of 500.00 Cr.
- **Diagnostic Evidence:** `{'rec_v02_diff': 500.0, 'rec_do02_diff': 499.99999999813735}`

### CORRUPT-E: MISSING_ENTITY_COLUMN
- **Target Location:** Table `raw_chapter_outward`, Field `Column 'BIHAR'`, Record `All 90 chapter dispatches for BIHAR`
- **Original Value:** `Column 'BIHAR' present (90 rows)`
- **Corrupted Value:** `Column 'BIHAR' dropped (leaving 32 state columns, 2,880 rows)`
- **Expected Detector:** COMPLETENESS_VALIDATION (CMP-03) / RECONCILIATION
- **Actual Detector:** CMP-03 (Completeness Validation) & REC-DO02 (Reconciliation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** CMP-03 caught missing BIHAR state records: expected 2970, observed 2880 (difference=90.0 records); REC-DO02 flagged cross-table imbalance of 41,390.96 Cr.
- **Diagnostic Evidence:** `{'missing_records': 90.0}`

### CORRUPT-F: NUMERIC_TO_TEXT
- **Target Location:** Table `state_chapter_internal`, Field `movement_value_inr_crore`, Record `chapter_code='10', state='MAHARASHTRA'`
- **Original Value:** `1457.697261449`
- **Corrupted Value:** `CORRUPTED_TEXT`
- **Expected Detector:** NUMERIC_VALIDATION (NUM-01)
- **Actual Detector:** NUM-01-state_chapter_internal (Numeric Validation)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `BLOCKED (Trusted loading halted)`
- **Detection Message:** NUM-01 caught non-numeric movement value: observed 1 non-numeric values (affected_records=1).
- **Diagnostic Evidence:** `{'non_numeric_count': 1}`

### CORRUPT-G: DISTRIBUTION_SHIFT
- **Target Location:** Table `state_outward`, Field `State Outward Freight Distribution`, Record `All 33 state outward dispatch volumes`
- **Original Value:** `Baseline distribution (KS p = 0.6543 vs FY 2022–23; PSI = 0.2341)`
- **Corrupted Value:** `Shifted distribution (100x scaling; KS p < 1e-7, PSI = 3.0118 >= 0.25)`
- **Expected Detector:** STATISTICAL_ANALYSIS (KS_TEST / PSI)
- **Actual Detector:** KS_TEST & PSI (Statistical Analysis Engine)
- **Detection Status:** `DETECTED`
- **Pipeline Blocking Behavior:** `NON-BLOCKING (Advisory monitoring signal)`
- **Detection Message:** Statistical engine detected controlled shift: KS statistic=0.7273, p-value=1.03e-08 (< 0.05); PSI=3.0118 (>= 0.25 threshold). Triggered STATISTICALLY_DIFFERENT advisory signal without blocking trusted loading.
- **Diagnostic Evidence:** `{'ks_statistic': 0.7272727272727273, 'ks_p_value': 1.0254033758572361e-08, 'psi_value': 3.011756619003113}`

---

## 4. Analysis of Pipeline Blocking Behavior

1. **Deterministic Blocking on Integrity Failures (Scenarios A, B, C, D, E, F):**
   - Any failure in the validation engine (Schema, Completeness, Uniqueness, Domain, Numeric, Structural, Source-Total) triggers a `FAIL` status with `CRITICAL` or `ERROR` severity.
   - The architecture enforces that normalized data in staging is **not** promoted to `trusted_*` status if any blocking check fails.
2. **Advisory Statistical Monitoring (Scenario G):**
   - Scenario G tests the statistical engine's sensitivity to distributional shifts.
   - Both two-sample KS and PSI tests successfully flagged the 10x top-state divergence as `STATISTICALLY_DIFFERENT`.
   - Crucially, statistical shifts do **not** trigger a pipeline block. Statistical difference represents an analytical signal of empirical divergence across annual snapshots, not a definitive indication of pipeline failure or data corruption.

---

## 5. Production Isolation & Source Immutability

- **Isolated In-Memory Copies:** Every corruption scenario operated on a deep copy of in-memory data structures (`deepcopy_dataset`).
- **No Database Contamination:** Corrupted records were never written to production warehouse tables (`trusted_state_movement`, `trusted_chapter_movement`, `trusted_state_chapter_outward`, `trusted_state_chapter_inward`, `trusted_state_chapter_internal`).
- **Source Workbooks Untouched:**
  - `data/Road_EwayBill_2022_23.xlsx`: `534ae64cdfe76ae1adbe5db789443cd5af5fc34df94925beba1949859d209aef` (Verified byte-for-byte identical)
  - `data/Road_EwayBill_2023_24.xlsx`: `42fdba9a6fcf40fb47f9a632d403b28680e610160db51cf75511163f59ce803d` (Verified byte-for-byte identical)

---

## 6. Methodological Limitations & Missed Detections

- **Zero Missed Detections:** All 7 controlled corruption scenarios were detected by their logically designated detector layers.
- **Layered Defense:** Structural and source-total discrepancies (Scenarios D and E) were caught redundantly by both the intra-table validation suite (`REC-V02`, `CMP-03`) and the cross-table reconciliation engine (`REC-DO02`, `REC-DO05`).
- **Limitations:** Controlled corruptions test synthetic single-point interventions. Compound corruptions where offsetting errors cancel out intra-table sums remain detectable only through orthogonal cross-table reconciliation audits.

