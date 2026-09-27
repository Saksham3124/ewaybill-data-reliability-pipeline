# Phase 7: Controlled Corruption Simulation & Detection Specification

**Document Version:** 1.0  
**Phase:** 7 — Controlled Corruption Simulation & Detection Testing  
**Evaluation Target:** Existing Data Reliability Pipeline (Validation Engine, Cross-Table Reconciliation Engine, YoY Statistical Analysis Engine)  
**Governance Scope:** Non-invasive evaluation of detection capability; original source workbooks and production warehouse tables remain strictly unmodified.

---

## 1. Objectives & Epistemic Principles

1. **Purpose:** Evaluate the empirical detection sensitivity of the data reliability framework against controlled, reproducible synthetic data defects.
2. **Detection Capability Testing:** Verify that each defect is identified by its logically designated detector layer without modifying or weakening existing validation, reconciliation, or statistical rules.
3. **Immutability of Source Data:** Original Excel workbooks (`Road_EwayBill_2022_23.xlsx` and `Road_EwayBill_2023_24.xlsx`) are never written to, updated, or manipulated.
4. **Strict Isolation:** All corruption injections are performed in-memory on isolated deep copies. Corrupted records are strictly barred from production warehouse tables (`trusted_*`).
5. **No Synthetic Normalization:** Defective data is never silently repaired, interpolated, or imputed.
6. **Separation of Integrity vs. Statistical Shift:**
   - Integrity defects (completeness, uniqueness, domain, numeric, source-total) trigger validation `FAIL` and halt trusted loading (`pipeline_blocked = True`).
   - Distributional shifts trigger statistical signals (`STATISTICALLY_DIFFERENT`), serving as non-blocking analytical monitoring signals (`pipeline_blocked = False`).

---

## 2. Controlled Corruption Scenarios

| Scenario ID | Corruption Category | Target Table | Target Location / Entity | Modification Description | Expected Detector | Blocking Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`CORRUPT-A`** | Missing State/Chapter Record | `state_chapter_outward` | Chapter 10, State `MAHARASHTRA` | Single logical record deleted (2,969 rows remaining) | `CMP-03` (Completeness Validation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-B`** | Duplicate Logical Record | `state_chapter_outward` | Chapter 10, State `MAHARASHTRA` | Identical duplicate record appended (2,971 rows total) | `UNQ-03` (Uniqueness Validation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-C`** | Invalid Chapter Domain | `chapter_movement` | Chapter 10 | Code mutated from valid `'10'` to invalid `'999'` | `DOM-03` (Domain Validation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-D`** | Altered Movement Value | `raw_chapter_outward` (Table III) | Chapter 10, State `MAHARASHTRA` | Value altered by $+500.00$ Cr without adjusting total row | `REC-V02` (Source-Total) & `REC-DO02`/`REC-DO05` (Reconciliation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-E`** | Missing State Entity Column | `raw_chapter_outward` (Table III) | Column `BIHAR` | Entire state column removed from Table III (leaving 32 state columns) | `CMP-03` (Completeness) & `REC-DO02` (Reconciliation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-F`** | Numeric-to-Text Corruption | `state_chapter_internal` | Chapter 10, State `MAHARASHTRA` | Numeric float replaced with textual string `'CORRUPTED_TEXT'` | `NUM-01` (Numeric Validation) | **BLOCKING** (`FAIL`) |
| **`CORRUPT-G`** | Controlled Distribution Shift | `raw_chapter_outward` / `state_outward` | All 33 state dispatch volumes | State volumes multiplied by $100.0\times$ in comparison year | `KS_TEST` & `PSI` (Statistical Analysis Engine) | **ADVISORY** (Non-blocking) |

---

## 3. Scenario Mechanics & Detection Criteria

### Scenario A: Missing State/Chapter Combination (`CORRUPT-A`)
- **Mechanism:** Remove row `(chapter_code='10', state='MAHARASHTRA')` from normalized DataFrame `state_chapter_outward`.
- **Pass/Fail Criteria:** Check `CMP-03` (`state_chapter_outward Record Completeness`) evaluates `len(df) == 2970`.
- **Detection Signal:** `CMP-03` yields status `FAIL`, observed = 2,969, difference = 1, severity = `CRITICAL`.
- **Pipeline Action:** Halts promotion to trusted storage.

### Scenario B: Duplicate Logical Record (`CORRUPT-B`)
- **Mechanism:** Append a duplicate instance of row `(chapter_code='10', state='MAHARASHTRA')` to `state_chapter_outward`.
- **Pass/Fail Criteria:** Check `UNQ-03` evaluates duplicate keys on `(chapter_code, state)`.
- **Detection Signal:** `UNQ-03` yields status `FAIL`, observed = 2 duplicates, severity = `CRITICAL`.
- **Pipeline Action:** Halts promotion to trusted storage.

### Scenario C: Invalid Chapter Code (`CORRUPT-C`)
- **Mechanism:** Mutate `chapter_code` for Chapter 10 to string `'999'` in `chapter_movement`.
- **Pass/Fail Criteria:** Check `DOM-03-chapter_movement` verifies 2-digit numeric codes within the 10–99 domain.
- **Detection Signal:** `DOM-03-chapter_movement` yields status `FAIL`, observed = `{'999'}`, severity = `ERROR`. (Also triggers `CMP-06` failure).
- **Pipeline Action:** Halts promotion to trusted storage.

### Scenario D: Altered Movement Value without Totals Update (`CORRUPT-D`)
- **Mechanism:** Modify cell in Table III raw matrix `(chapter_code=10, column=MAHARASHTRA)` by adding $+500.00$ Crore. Row 93 reported state column total is unmodified.
- **Pass/Fail Criteria:**
  - `REC-V02` checks sum of Table III column cells against row 93 reported total.
  - `REC-DO02` audits cross-table outward vs inward equality.
  - `REC-DO05` audits Table I row marginal vs Table III total for Maharashtra.
- **Detection Signal:** `REC-V02` yields status `FAIL` (difference = 500.0 Cr > tolerance 0.0001 Cr); `REC-DO02` and `REC-DO05` yield `WARNING`.
- **Pipeline Action:** Halts promotion to trusted storage due to `REC-V02` validation failure.

### Scenario E: Missing State from One Table (`CORRUPT-E`)
- **Mechanism:** Remove column `'BIHAR'` from `raw_chapter_outward` (Table III) while retaining it across all other sheets.
- **Pass/Fail Criteria:** Normalized `state_chapter_outward` contains only 2,880 rows ($32 \times 90$).
- **Detection Signal:** `CMP-03` yields status `FAIL` (observed 2,880 vs expected 2,970, difference = 90 rows); `REC-DO02` flags outward deficit.
- **Pipeline Action:** Halts promotion to trusted storage.

### Scenario F: Numeric-to-Text Corruption (`CORRUPT-F`)
- **Mechanism:** Replace float in `movement_value_inr_crore` with non-numeric string `'CORRUPTED_TEXT'` in `state_chapter_internal`.
- **Pass/Fail Criteria:** `NUM-01-state_chapter_internal` validates that every non-null entry is numeric.
- **Detection Signal:** `NUM-01-state_chapter_internal` yields status `FAIL` (affected records = 1), severity = `ERROR`.
- **Pipeline Action:** Halts promotion to trusted storage.

### Scenario G: Controlled Distribution Shift (`CORRUPT-G`)
- **Mechanism:** Scale all state outward dispatch volumes in FY 2023–24 by $100.0\times$ relative to FY 2022–23 baseline.
- **Pass/Fail Criteria:** Two-sample KS test compares eCDFs; PSI test quantifies baseline quantile stability.
- **Detection Signal:** Two-sample KS test yields $p = 1.03 \times 10^{-8} < 0.05$ (`STATISTICALLY_DIFFERENT`); PSI test yields $3.0118 \ge 0.25$ (`STATISTICALLY_DIFFERENT`).
- **Pipeline Action:** Generates high-priority analytical advisory signal. **Does NOT block trusted loading** (statistical difference is an advisory finding of empirical shift, not proof of technical failure).

---

## 4. Test Isolation Architecture

1. **In-Memory Deep Copies:** `deepcopy_dataset` isolates raw matrices and normalized tables prior to applying mutations.
2. **Zero Production Mutation:** Corrupted records never touch PostgreSQL `trusted_*` or `raw_*` tables.
3. **Byte-Level Verification:** Both reference and comparison Excel files are verified via SHA-256 before and after every simulation execution:
   - `data/Road_EwayBill_2022_23.xlsx`: `534ae64cdfe76ae1adbe5db789443cd5af5fc34df94925beba1949859d209aef`
   - `data/Road_EwayBill_2023_24.xlsx`: `42fdba9a6fcf40fb47f9a632d403b28680e610160db51cf75511163f59ce803d`
