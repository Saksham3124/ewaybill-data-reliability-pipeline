# Data Reconciliation Specification

**Target Dataset:** `data/Road_EwayBill_2023_24.xlsx`  
**Issuing Authority:** DGCI&S, Ministry of Commerce and Industry, Government of India  
**Scope:** E-Way Bill Road Movement Freight Reconciliation  
**Document Status:** Pre-Implementation Specification (Methodology Verification Phase)

---

## 1. Reconciliation Governance & Rule Taxonomy

To safeguard data integrity and prevent arbitrary or speculative assertions from entering production pipelines, every reconciliation rule is classified under four strict categories:

1. **`VERIFIED`**: Explicitly supported by the source workbook's own layout, defined totals, and structural design. Safe for automated assertion in production pipelines.
2. **`DATA-OBSERVED`**: Empirically and mathematically verified across data points, but lacking explicit documentation in the source metadata. Requires confirmation of official methodology before being promoted to hard blocking rules.
3. **`HYPOTHESIS`**: Plausible structural or economic interpretation that fits observed patterns but remains unproven. Must not be used as an enforcement gate.
4. **`NOT VALID`**: Formally rejected rules. Includes relationships that fail numerical tests or that make unsupported assumptions that distort data.

---

## 2. Category 1: VERIFIED Reconciliation Rules

The following rules represent **intra-table consistency checks** where the source workbook explicitly defines summary rows, summary columns, or header aggregations. These rules are **safe to implement immediately**.

---

### Rule REC-V01: Table II Internal Row Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab II_Chap_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Column D (`VALUE (in INR Crore)`).
  - Summary Range: Row 93, Column D (`TOTAL VALUE (in INR Crore)---->>`).
- **Transformation:** Direct vertical sum of all chapter values.
- **Formula:**
  $$\sum_{r=3}^{92} \text{Table\_II}[r, \text{Col D}] = \text{Table\_II}[93, \text{Col D}]$$
- **Expected Value:** `20,319,786.98011017` INR Crore
- **Observed Value:** `20,319,786.98011017` INR Crore
- **Difference:** `0.000000000000` INR Crore
- **Tolerance:** `0.0001` INR Crore (accounting for 64-bit float summation)
- **Interpretation:** Verifies that the individual commodity chapter values in Table II sum exactly to the reported national total.
- **PASS/FAIL Rule:**
  $$\text{IF } \left| \sum_{r=3}^{92} \text{Table\_II}[r, \text{Col D}] - \text{Table\_II}[93, \text{Col D}] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V02: Table III Column-Wise State Outward Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab III_Outward_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Columns D to AJ (33 States/UTs).
  - Summary Range: Row 93, Columns D to AJ (`OUTWARD VALUE (in INR Crore) ----->>`).
- **Transformation:** Vertical summation of all chapter rows for each state column $c \in [4, 36]$ (treating empty cells `None` as `0.0`).
- **Formula:**
  $$\forall c \in [4, 36]: \quad \sum_{r=3}^{92} \text{Table\_III}[r, c] = \text{Table\_III}[93, c]$$
- **Expected Values:** 33 published state outward totals in Row 93.
- **Observed Values:** Exact match across all 33 states.
- **Max Difference:** $2.33 \times 10^{-10}$ INR Crore
- **Tolerance:** `0.0001` INR Crore per state
- **Interpretation:** Validates that the reported outward movement total for each state is the exact sum of its chapter-level dispatches.
- **PASS/FAIL Rule:**
  $$\text{IF } \max_{c \in [4, 36]} \left| \sum_{r=3}^{92} \text{Table\_III}[r, c] - \text{Table\_III}[93, c] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V03: Table IV Column-Wise State Inward Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab IV_Inward_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Columns D to AJ (33 States/UTs).
  - Summary Range: Row 93, Columns D to AJ (`INWARD VALUE (in INR Crore) ----->>`).
- **Transformation:** Vertical summation of chapter rows for each state column $c \in [4, 36]$ (treating `None` as `0.0`).
- **Formula:**
  $$\forall c \in [4, 36]: \quad \sum_{r=3}^{92} \text{Table\_IV}[r, c] = \text{Table\_IV}[93, c]$$
- **Expected Values:** 33 published state inward totals in Row 93.
- **Observed Values:** Exact match across all 33 states.
- **Max Difference:** $2.33 \times 10^{-10}$ INR Crore
- **Tolerance:** `0.0001` INR Crore per state
- **Interpretation:** Validates that reported inward receipts for each state equal the sum of chapter-level arrivals.
- **PASS/FAIL Rule:**
  $$\text{IF } \max_{c \in [4, 36]} \left| \sum_{r=3}^{92} \text{Table\_IV}[r, c] - \text{Table\_IV}[93, c] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V04: Table IV Row-Wise Chapter Inward Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab IV_Inward_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Columns D to AJ (33 States/UTs).
  - Summary Range: Column AK (`TOTAL`), Rows 3 to 92.
- **Transformation:** Horizontal summation of all state columns for each chapter row $r \in [3, 92]$ (treating `None` as `0.0`).
- **Formula:**
  $$\forall r \in [3, 92]: \quad \sum_{c=4}^{36} \text{Table\_IV}[r, c] = \text{Table\_IV}[r, 37]$$
- **Expected Values:** 90 published chapter totals in Column AK.
- **Observed Values:** Exact match across all 90 chapters.
- **Max Difference:** $0.000000000000$ INR Crore
- **Tolerance:** `0.0001` INR Crore per chapter
- **Interpretation:** Validates that each chapter's published national inward total equals the sum of its receipts across all 33 jurisdictions.
- **PASS/FAIL Rule:**
  $$\text{IF } \max_{r \in [3, 92]} \left| \sum_{c=4}^{36} \text{Table\_IV}[r, c] - \text{Table\_IV}[r, 37] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V05: Table IV Dual-Dimension Grand Total Cross-Foot
- **Classification:** `VERIFIED`
- **Source Table:** `Tab IV_Inward_Revised_Road`
- **Row/Column Dimensions:**
  - Column Summary: Row 93, Columns D to AJ (`INWARD VALUE`).
  - Row Summary: Column AK, Rows 3 to 92 (`TOTAL`).
  - Corner Cell: Cell `AK93` (Row 93, Col 37).
- **Transformation:** Independent summation across both axes.
- **Formula:**
  $$\sum_{c=4}^{36} \text{Table\_IV}[93, c] = \text{Table\_IV}[93, 37] = \sum_{r=3}^{92} \text{Table\_IV}[r, 37]$$
- **Expected Value:** `10,429,324.40404665` INR Crore
- **Observed Values:**
  - Sum of State Column Totals: `10,429,324.404046647` INR Crore
  - Sum of Chapter Row Totals: `10,429,324.40404665` INR Crore
  - Cell `AK93`: `10,429,324.40404665` INR Crore
- **Difference:** $3.72 \times 10^{-9}$ INR Crore
- **Tolerance:** `0.0001` INR Crore
- **Interpretation:** Confirms two-dimensional mathematical consistency across the entire inward matrix.
- **PASS/FAIL Rule:**
  $$\text{IF } \left| \sum_{c=4}^{36} \text{Table\_IV}[93, c] - \text{Table\_IV}[93, 37] \right| \le 0.0001 \text{ AND } \left| \sum_{r=3}^{92} \text{Table\_IV}[r, 37] - \text{Table\_IV}[93, 37] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V06: Table V Column-Wise State Internal Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab V_Internal_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Columns D to AJ (33 States/UTs).
  - Summary Range: Row 93, Columns D to AJ (`INTERNAL VALUE (in INR Crore) ----->>`).
- **Transformation:** Vertical summation of chapter rows for each state column $c \in [4, 36]$ (treating `None` as `0.0`).
- **Formula:**
  $$\forall c \in [4, 36]: \quad \sum_{r=3}^{92} \text{Table\_V}[r, c] = \text{Table\_V}[93, c]$$
- **Expected Values:** 33 published state internal totals in Row 93.
- **Observed Values:** Exact match across all 33 states.
- **Max Difference:** $1.86 \times 10^{-9}$ INR Crore
- **Tolerance:** `0.0001` INR Crore per state
- **Interpretation:** Validates that reported intra-state movement for each state equals the sum of its chapter-level intra-state dispatches.
- **PASS/FAIL Rule:**
  $$\text{IF } \max_{c \in [4, 36]} \left| \sum_{r=3}^{92} \text{Table\_V}[r, c] - \text{Table\_V}[93, c] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V07: Table V Row-Wise Chapter Internal Summation
- **Classification:** `VERIFIED`
- **Source Table:** `Tab V_Internal_Revised_Road`
- **Row/Column Dimensions:**
  - Data Range: Rows 3 to 92 (90 HS Chapters), Columns D to AJ (33 States/UTs).
  - Summary Range: Column AK (`TOTAL`), Rows 3 to 92.
- **Transformation:** Horizontal summation of all state columns for each chapter row $r \in [3, 92]$ (treating `None` as `0.0`).
- **Formula:**
  $$\forall r \in [3, 92]: \quad \sum_{c=4}^{36} \text{Table\_V}[r, c] = \text{Table\_V}[r, 37]$$
- **Expected Values:** 90 published chapter totals in Column AK.
- **Observed Values:** Exact match across all 90 chapters.
- **Max Difference:** $1.82 \times 10^{-12}$ INR Crore
- **Tolerance:** `0.0001` INR Crore per chapter
- **Interpretation:** Validates that each chapter's published national internal total equals the sum of its intra-state flows across all 33 jurisdictions.
- **PASS/FAIL Rule:**
  $$\text{IF } \max_{r \in [3, 92]} \left| \sum_{c=4}^{36} \text{Table\_V}[r, c] - \text{Table\_V}[r, 37] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

### Rule REC-V08: Table V Dual-Dimension Grand Total Cross-Foot
- **Classification:** `VERIFIED`
- **Source Table:** `Tab V_Internal_Revised_Road`
- **Row/Column Dimensions:**
  - Column Summary: Row 93, Columns D to AJ (`INTERNAL VALUE`).
  - Row Summary: Column AK, Rows 3 to 92 (`TOTAL`).
  - Corner Cell: Cell `AK93` (Row 93, Col 37).
- **Transformation:** Independent summation across both axes.
- **Formula:**
  $$\sum_{c=4}^{36} \text{Table\_V}[93, c] = \text{Table\_V}[93, 37] = \sum_{r=3}^{92} \text{Table\_V}[r, 37]$$
- **Expected Value:** `9,890,462.576063517` INR Crore
- **Observed Values:**
  - Sum of State Column Totals: `9,890,462.576063516` INR Crore
  - Sum of Chapter Row Totals: `9,890,462.576063516` INR Crore
  - Cell `AK93`: `9,890,462.576063517` INR Crore
- **Difference:** $1.00 \times 10^{-12}$ INR Crore
- **Tolerance:** `0.0001` INR Crore
- **Interpretation:** Confirms two-dimensional mathematical consistency across the entire internal matrix.
- **PASS/FAIL Rule:**
  $$\text{IF } \left| \sum_{c=4}^{36} \text{Table\_V}[93, c] - \text{Table\_V}[93, 37] \right| \le 0.0001 \text{ AND } \left| \sum_{r=3}^{92} \text{Table\_V}[r, 37] - \text{Table\_V}[93, 37] \right| \le 0.0001 \implies \mathbf{PASS} \text{ ELSE } \mathbf{FAIL}$$

---

## 3. Category 2: DATA-OBSERVED Relationships

These relationships hold mathematically across worksheets but are **not explicitly defined in source documentation**. They must be monitored as advisory checks rather than hard pipeline blocks until verified with official methodology.

---

### Relationship REC-DO01: National Total Movement Equivalence
- **Classification:** `DATA-OBSERVED`
- **Source Tables:** `Tab I_Stat_to_Stat_Revised_Road`, `Tab II_Chap_Revised_Road`
- **Formula:**
  $$\sum_{r=4}^{36} \sum_{c=3}^{35} \text{Table\_I}[r, c] = \text{Table\_II}[93, \text{Col D}]$$
- **Expected Value:** `20,319,786.98011017` INR Crore
- **Observed Value:** `20,319,786.98011017` INR Crore
- **Difference:** `0.000000000000` INR Crore
- **Governance Note:** The source contains no text linking Table I's matrix sum to Table II's total. It is an empirical finding that Table I encompasses the full national movement captured in Table II.

---

### Relationship REC-DO02: Closed National System Outward/Inward Equality
- **Classification:** `DATA-OBSERVED`
- **Source Tables:** `Tab III_Outward_Revised_Road`, `Tab IV_Inward_Revised_Road`
- **Formula:**
  $$\sum_{c=4}^{36} \text{Table\_III}[93, c] = \text{Table\_IV}[93, 37]$$
- **Expected Value:** `10,429,324.40404665` INR Crore
- **Observed Difference:** `0.000000000000` INR Crore (within float precision: $3.72 \times 10^{-9}$)
- **Governance Note:** While logically sound for a closed domestic economy, the issuing authority does not publish a statement defining national outward and inward as reciprocal aggregates.

---

### Relationship REC-DO03: Composite National Total Partitioning
- **Classification:** `DATA-OBSERVED`
- **Source Tables:** `Tab II_Chap_Revised_Road`, `Tab III_Outward_Revised_Road`, `Tab IV_Inward_Revised_Road`, `Tab V_Internal_Revised_Road`
- **Formula:**
  $$\text{Table\_II Total} = \sum \text{Table\_III (Outward)} + \sum \text{Table\_V (Internal)}$$
  $$\text{Table\_II Total} = \sum \text{Table\_IV (Inward)} + \sum \text{Table\_V (Internal)}$$
- **Observed Values:**
  - Outward + Internal: $10,429,324.40404665 + 9,890,462.57606352 = \mathbf{20,319,786.98011017}$ Crore
  - Inward + Internal: $10,429,324.40404665 + 9,890,462.57606352 = \mathbf{20,319,786.98011017}$ Crore
  - Table II Total: $\mathbf{20,319,786.98011017}$ Crore
- **Difference:** $-7.45 \times 10^{-9}$ INR Crore ($< ₹0.01$)
- **Governance Note:** Demonstrates that Table II is composed of inter-state movements plus intra-state movements. This composite relationship is unstated in the source.

---

### Relationship REC-DO04: State Marginal Column Conservation
- **Classification:** `DATA-OBSERVED`
- **Source Tables:** `Tab I_Stat_to_Stat_Revised_Road`, `Tab III_Outward_Revised_Road`, `Tab V_Internal_Revised_Road`
- **Formula:**
  $$\forall j \in [1, 33]: \quad \sum_{r=4}^{36} \text{Table\_I}[r, j+2] = \text{Table\_III}[93, j+3] + \text{Table\_V}[93, j+3]$$
- **Observed Difference:** Max difference across all 33 states $\le 9.31 \times 10^{-10}$ INR Crore.
- **Governance Note:** Holds universally across all 33 jurisdictions, including `OTHER TERRITORY`.

---

### Relationship REC-DO05: State Marginal Row Conservation
- **Classification:** `DATA-OBSERVED`
- **Source Tables:** `Tab I_Stat_to_Stat_Revised_Road`, `Tab IV_Inward_Revised_Road`, `Tab V_Internal_Revised_Road`
- **Formula:**
  $$\forall i \in [1, 33]: \quad \sum_{c=3}^{35} \text{Table\_I}[i+3, c] = \text{Table\_IV}[93, i+3] + \text{Table\_V}[93, i+3]$$
- **Observed Difference:** Max difference across all 33 states $\le 1.40 \times 10^{-9}$ INR Crore.
- **Governance Note:** Holds universally across all 33 jurisdictions, including `OTHER TERRITORY`.

---

### Relationship REC-DO06: Non-Other-Territory Diagonal Equivalence
- **Classification:** `DATA-OBSERVED` (Qualified: 32 of 33 States Only)
- **Source Tables:** `Tab I_Stat_to_Stat_Revised_Road`, `Tab V_Internal_Revised_Road`
- **Formula:**
  $$\forall k \in \{1 \dots 33\} \setminus \{\text{OTHER TERRITORY}\}: \quad \text{Table\_I}[k+3, k+2] = \text{Table\_V}[93, k+3]$$
- **Observed Difference:** `0.000000000000` INR Crore for all 32 states/UTs.
- **Governance Note:** This relationship is exact for 32 entities, but fails for `OTHER TERRITORY` by ₹76,614.93 Crore.

---

## 4. Specific Treatment of OTHER TERRITORY

### UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION

The source profiling identified the following discrepancy for `OTHER TERRITORY`:

| Metric | Source Location | Value (INR Crore) |
| :--- | :--- | :--- |
| Table I Diagonal (`OTHER TERRITORY -> OTHER TERRITORY`) | Sheet 1, Cell `Y26` (Row 26, Col 25) | **₹258,324.421758** |
| Table V Internal Total | Sheet 5, Row 93, Col 26 | **₹181,709.488219** |
| **Numerical Divergence** | $\Delta = S_1[\text{OT}, \text{OT}] - S_5[\text{TOTAL}, \text{OT}]$ | **$+₹76,614.933539$** |

### Mandatory Governance Constraints:
1. **No Invented Explanations:** The issuing authority (DGCI&S) provides no explanatory note, footnote, or documentation clarifying why Table I diagonal exceeds Table V internal total by ₹76,614.93 Crore for `OTHER TERRITORY`.
2. **Status Declaration:** This discrepancy is officially designated as:
   > **"UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION"**
3. **Prohibition of Data Mutation:** Pipelines and reconciliation scripts must **NOT** alter, reallocate, or force-balance this discrepancy.
4. **Rejection as a Blanket Rule:** Any reconciliation rule asserting that `Table I Diagonal == Table V Internal` across all 33 jurisdictions is **categorically rejected**.

---

## 5. Category 3: INFERENCES & HYPOTHESES

These interpretations represent plausible domain hypotheses. They are documented for analytical context but must **never** be used as blocking gates in production data pipelines.

- **`HYP-01` (Table I Directionality):**  
  *Hypothesis:* Columns represent Origin ("From State") and Rows represent Destination ("To State").  
  *Status:* Highly consistent with data, but unverified by official source documentation.
- **`HYP-02` (Diagonal Semantics):**  
  *Hypothesis:* Table I diagonal represents intra-state movements.  
  *Status:* Supported for 32 states; unresolved for `OTHER TERRITORY`.
- **`HYP-03` (Statutory Exemption of Chapters 01–09):**  
  *Hypothesis:* The absence of HS Chapters 01–09 is due to CGST Rule 138(14) agricultural exemptions.  
  *Status:* Plausible statutory context; not documented in the dataset.
- **`HYP-04` (Empty Cell Semantics):**  
  *Hypothesis:* Null/empty cells represent true zeros ($0.0$).  
  *Status:* Mathematically validated by exact sum convergence; requires official methodology sign-off.

---

## 6. Category 4: NOT VALID Rules (Explicitly Rejected)

The following rules must **NOT** be implemented in the reconciliation suite:

| Rule Code | Proposed Rule Description | Reason for Rejection |
| :--- | :--- | :--- |
| **`REC-NV01`** | `Table_I Diagonal[k] == Table_V Internal[k]` for all 33 jurisdictions | **Fails on data:** Fails by ₹76,614.93 Crore on `OTHER TERRITORY`. Implementing this as a universal rule will cause pipeline failure. |
| **`REC-NV02`** | `Table_I Row Off-Diagonal Sum == Table_III Outward Total` | **Fails on data:** Inverts directionality; produces errors exceeding ₹513,102 Crore. |
| **`REC-NV03`** | Automated adjustment or imputation of the ₹76,614.93 Crore difference in `OTHER TERRITORY` | **Violates data integrity:** Altering source data without official DGCI&S methodology constitutes ungrounded data tampering. |
| **`REC-NV04`** | Blocking pipeline on missing Chapters 01 to 09 | **Invalid expectation:** Chapters 01 to 09 are not part of the source dataset. |

---

## 7. Executive Summary of Implementation Roadmap

### A. Reconciliation Rules Safe to Implement Immediately
These rules are intra-table mathematical checks derived directly from the source workbook's structure:
1. `REC-V01`: Table II Chapter Row Summation vs. Row 93 Total.
2. `REC-V02`: Table III Chapter Rows Summation vs. Row 93 State Outward Totals.
3. `REC-V03`: Table IV Chapter Rows Summation vs. Row 93 State Inward Totals.
4. `REC-V04`: Table IV State Columns Summation vs. Column AK Chapter Totals.
5. `REC-V05`: Table IV Dual-Dimension Grand Total Cross-Foot (`AK93`).
6. `REC-V06`: Table V Chapter Rows Summation vs. Row 93 State Internal Totals.
7. `REC-V07`: Table V State Columns Summation vs. Column AK Chapter Totals.
8. `REC-V08`: Table V Dual-Dimension Grand Total Cross-Foot (`AK93`).

---

### B. Relationships Requiring Manual Methodology Verification
These relationships hold across tables but must be treated as advisory warnings until confirmed with DGCI&S:
1. `REC-DO01`: Table I Total Matrix Sum vs. Table II National Total (`20,319,786.98` Crore).
2. `REC-DO02`: National Outward Total vs. National Inward Total (`10,429,324.40` Crore).
3. `REC-DO03`: National Total Movement vs. (Outward + Internal) and (Inward + Internal).
4. `REC-DO04`: State-Level Marginal Column Sum vs. (Outward + Internal) across 33 states.
5. `REC-DO05`: State-Level Marginal Row Sum vs. (Inward + Internal) across 33 states.
6. `REC-DO06`: Table I Diagonal vs. Table V Internal for the 32 non-Other-Territory states.

---

### C. Relationships That Must NOT Yet Be Implemented
These rules are prohibited from implementation:
1. `REC-NV01`: Universal Diagonal Equality across all 33 jurisdictions (blocked by `OTHER TERRITORY`).
2. `REC-NV02`: Inverted Table I Directionality (Row = Outward).
3. `REC-NV03`: Forced balancing, mutation, or reconciliation of the ₹76,614.93 Crore `OTHER TERRITORY` discrepancy.
4. `REC-NV04`: Schema integrity checks asserting presence of HS Chapters 01 to 09.
