# Historical Source Profiling Report: FY 2022–23 vs. FY 2023–24

**Target Baseline Dataset:** `data/Road_EwayBill_2022_23.xlsx`  
**Target Reference Dataset:** `data/Road_EwayBill_2023_24.xlsx`  
**Issuing Authority:** Directorate General of Commercial Intelligence and Statistics (DGCI&S), Ministry of Commerce and Industry, Government of India  
**Scope:** Structural Comparability and Baseline Integrity Assessment  
**Evaluation Date:** September 2026  

---

## 1. Executive Summary & Epistemic Taxonomy

Before utilizing the newly added FY 2022–23 workbook as a historical statistical baseline, this profiling phase establishes whether it is structurally and semantically comparable with the FY 2023–24 production workbook.

To adhere strictly to data reliability governance, every statement, finding, and relationship in this report is categorized according to three evidentiary tiers:
1. **`DOCUMENTED BY SOURCE`**: Information explicitly stated in worksheet titles, table headers, column labels, summary markers, or source metadata.
2. **`OBSERVED FROM DATA`**: Mathematically and empirically computed properties directly observed from data cell distributions and programmatic inspection.
3. **`INFERENCE / HYPOTHESIS`**: Interpretative domain deductions. These are explicitly marked and never asserted as source facts.

### High-Level Comparability Verdict

> [!IMPORTANT]
> **COMPARABILITY ASSESSMENT VERDICT:**  
> The FY 2022–23 and FY 2023–24 workbooks are **`STRUCTURALLY COMPARABLE WITH CONTROLLED ADAPTATIONS`**.  
> - **Core Dimensions:** Both workbooks feature the exact same 5 worksheets, 33 geographic jurisdictions, and 90 HS chapters (Chapters 10–99).
> - **Primary Structural Discrepancy:** In FY 2022–23, Table III includes a national row-summary column (Column AK, `VALUE (in INR Crore)`), which was omitted from the 2023–24 workbook.
> - **Label Variations:** Exact jurisdictions match 100%, but 2 jurisdictions exhibit spelling variations (`CHHATTISGARH` vs. `CHATTISGARH`, `JAMMU AND KASHMIR` vs. `JAMMU & KASHMIR`), and Table V in 2022–23 uses Title Case `Other Territory`.
> - **Mathematical Consistency:** The 2022–23 workbook exhibits complete internal and cross-table mathematical harmony ($100\%$ match across all 6 cross-table audits, including `OTHER TERRITORY`).

---

## 2. Source Workbooks Profile & File Integrity

Both workbooks were accessed strictly in read-only mode. Their file metadata and cryptographic SHA-256 signatures are recorded below:

| Property | FY 2022–23 Historical Baseline | FY 2023–24 Production Reference | Status Classification |
| :--- | :--- | :--- | :---: |
| **File Name** | `Road_EwayBill_2022_23.xlsx` | `Road_EwayBill_2023_24.xlsx` | `DOCUMENTED BY SOURCE` |
| **File Size** | `173,969 bytes` | `169,188 bytes` | `OBSERVED FROM DATA` |
| **SHA-256 Hash** | `534ae64cdfe76ae1adbe5db789443cd5af5fc34df94925beba1949859d209aef` | `42fdba9a6fcf40fb47f9a632d403b28680e610160db51cf75511163f59ce803d` | `OBSERVED FROM DATA` |
| **Worksheet Count** | 5 | 5 | `COMPARABLE` |
| **Formula Count** | 0 (Static numeric values) | 0 (Static numeric values) | `COMPARABLE` |
| **Underlying Engine** | openpyxl / Excel XLSX | openpyxl / Excel XLSX | `COMPARABLE` |

---

## 3. Side-by-Side Worksheet Catalog & Dimensional Comparison

Both workbooks contain the exact same five worksheet names in identical sequential order. However, their active boundaries and summary columns show subtle structural differences:

| Sheet Name | FY 2022–23 Dimensions | FY 2023–24 Dimensions | Data Range | Difference Classification |
| :--- | :---: | :---: | :---: | :---: |
| **`Tab I_Stat_to_Stat_Revised_Road`** | Rows 1–36, Cols 2–35 ($33 \times 33$) | Rows 1–36, Cols 2–35 ($33 \times 33$) | Rows 4–36, Cols 3–35 | **`COMPARABLE`** |
| **`Tab II_Chap_Revised_Road`** | Rows 1–93, Cols 2–4 ($90 \times 1$) | Rows 1–93, Cols 2–4 ($90 \times 1$) | Rows 3–92, Col 4 | **`COMPARABLE`** |
| **`Tab III_Outward_Revised_Road`** | Rows 1–93, Cols 2–**37** ($90 \times 33$ + Col AK) | Rows 1–93, Cols 2–**36** ($90 \times 33$, no Col AK) | Rows 3–92, Cols 4–36 | **`STRUCTURAL DIFFERENCE`** |
| **`Tab IV_Inward_Revised_Road`** | Rows 1–93, Cols 2–37 ($90 \times 33$ + Col AK) | Rows 1–93, Cols 2–37 ($90 \times 33$ + Col AK) | Rows 3–92, Cols 4–36 | **`COMPARABLE`** |
| **`Tab V_Internal_Revised_Road`** | Rows 1–93, Cols 2–37 ($90 \times 33$ + Col AK) | Rows 1–93, Cols 2–37 ($90 \times 33$ + Col AK) | Rows 3–92, Cols 4–36 | **`COMPARABLE`** |

### Structural Finding: Table III Column AK Availability
- **In FY 2022–23 (`OBSERVED FROM DATA`):** Table III includes Column 37 (Column `AK`) with header `VALUE (in INR Crore)`. Cell `AK3` to `AK92` provide exact row-wise chapter outward sums across all 33 states, and cell `AK93` contains national outward total `62,999,856.00740427` INR Crore.
- **In FY 2023–24 (`OBSERVED FROM DATA`):** Table III contains data up to Column 36 (Column `AJ`, `WEST BENGAL`). Column `AK` is completely blank/unpopulated.
- **Classification:** **`STRUCTURAL DIFFERENCE`**. The 2022–23 Table III provides a chapter-level marginal summary that is absent in 2023–24.

---

## 4. Jurisdiction & Geographic Entity Comparison

### 4.1 Count and Coverage
- **FY 2022–23 Jurisdiction Count (`OBSERVED FROM DATA`):** Exactly 33 states/UTs/territories.
- **FY 2023–24 Jurisdiction Count (`OBSERVED FROM DATA`):** Exactly 33 states/UTs/territories.
- **Set Equality:** The underlying geographic entities represented are 100% identical.
- **Sequence / Ordering:** The geographic ordering from Column D (`ANDHRA PRADESH`) to Column AJ (`WEST BENGAL`) is 100% identical in both years.

### 4.2 State Spelling & Label Variations
Across both workbooks, three label spelling variations are observed between 2022–23 and 2023–24:

| Canonical Entity | FY 2022–23 Source Label | FY 2023–24 Source Label | Worksheets Affected | Classification |
| :--- | :--- | :--- | :--- | :---: |
| **Chhattisgarh** | `CHHATTISGARH` (double 'H') | `CHATTISGARH` (single 'H') | Tab I (Cols & Rows), Tab III, IV, V | **`LABEL DIFFERENCE`** |
| **Jammu & Kashmir** | `JAMMU AND KASHMIR` (word 'AND') | `JAMMU & KASHMIR` (ampersand '&') | Tab I (Cols & Rows), Tab III, IV, V | **`LABEL DIFFERENCE`** |
| **Other Territory** | `Other Territory` (Title Case in Tab V; uppercase elsewhere) | `OTHER TERRITORY` (Uppercase across all sheets) | Tab V Column 26 header | **`LABEL DIFFERENCE`** |

> [!NOTE]
> In FY 2022–23 Table I:
> - Origin Column 8 header: `CHHATTISGARH`
> - Destination Row 9 header: `CHHATTISGARH`
> - Origin Column 14 header: `JAMMU AND KASHMIR`
> - Destination Row 15 header: `JAMMU AND KASHMIR`
> Unlike some datasets with intra-sheet naming drift, the 2022–23 Table I internal column and row headers are mutually consistent.

---

## 5. Commodity Chapter Comparison (HS Chapters 10–99)

- **Chapter Set (`DOCUMENTED BY SOURCE`):** Exactly 90 HS Commodity Chapters, numbered `10` through `99`.
- **Statutory Scope:** Chapters `01` through `09` are absent from both workbooks (`DOCUMENTED BY SOURCE` as absent; reason for absence classified as `INFERENCE / HYPOTHESIS`).
- **Chapter Ordering (`OBSERVED FROM DATA`):** Chapters are sorted in strictly ascending numerical order (`10`, `11`, ..., `99`) in Rows 3 to 92 across both workbooks.
- **Chapter Descriptions (`OBSERVED FROM DATA`):** All 90 chapter descriptions in Table II, III, IV, and V are **100% character-by-character identical** between FY 2022–23 and FY 2023–24. Zero discrepancies.

---

## 6. Units of Measurement & Scale Comparison

- **Stated Currency Units (`DOCUMENTED BY SOURCE`):** `INR Crore` (or `Value in INR Crore`) stated in title rows and summary headers of all worksheets across both years.
- **National Aggregates (`OBSERVED FROM DATA`):**
  - FY 2022–23 Table II National Total: **`94,353,264.74964216` INR Crore**
  - FY 2023–24 Table II National Total: **`20,319,786.98011017` INR Crore**
  - Ratio: FY 2022–23 national total is approximately $4.64\times$ the FY 2023–24 national total.
- **Outward / Inward Inter-State Totals (`OBSERVED FROM DATA`):**
  - FY 2022–23 Outward Grand Total: **`62,999,856.00740426` INR Crore**
  - FY 2023–24 Outward Grand Total: **`10,429,324.40404665` INR Crore**
- **Internal Intra-State Totals (`OBSERVED FROM DATA`):**
  - FY 2022–23 Internal Grand Total: **`31,353,408.74223777` INR Crore**
  - FY 2023–24 Internal Grand Total: **`9,890,462.57606352` INR Crore**

> [!NOTE]
> The substantial difference in national magnitude between FY 2022–23 and FY 2023–24 is an empirical observation from the raw published data. Determining whether this reflects macro-economic changes, reporting thresholds, or e-way bill generation parameters is classified as **`INFERENCE / HYPOTHESIS`** and is not asserted as source fact.

---

## 7. Data Sparsity & NULL Cell Distribution Comparison

Empty/blank cells represent non-occurring freight movements and are preserved as `NULL` across both workbooks:

| Worksheet | FY 2022–23 NULL Cells | FY 2023–24 NULL Cells | Total Data Cells | 2022–23 Sparsity | 2023–24 Sparsity |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`Tab I_Stat_to_Stat_Revised_Road`** | 2 | 5 | 1,089 | 0.18% | 0.46% |
| **`Tab II_Chap_Revised_Road`** | 0 | 0 | 90 | 0.00% | 0.00% |
| **`Tab III_Outward_Revised_Road`** | 65 | 108 | 2,970 | 2.19% | 3.64% |
| **`Tab IV_Inward_Revised_Road`** | 16 | 27 | 2,970 | 0.54% | 0.91% |
| **`Tab V_Internal_Revised_Road`** | 108 | 164 | 2,970 | 3.64% | 5.52% |
| **Total Pipeline NULL Cells** | **191** | **304** | **10,089** | **1.89%** | **3.01%** |

### Specific Zero-Movement Pairs in Table I
- **FY 2022–23 (2 NULL cells):**
  1. `GOA` destination $\leftarrow$ `MIZORAM` origin (Cell `V11`)
  2. `SIKKIM` destination $\leftarrow$ `MIZORAM` origin (Cell `V30`)
- **FY 2023–24 (5 NULL cells):**
  1. `CHANDIGARH` destination $\leftarrow$ `ARUNACHAL PRADESH` origin
  2. `GOA` destination $\leftarrow$ `ARUNACHAL PRADESH` origin
  3. `MIZORAM` destination $\leftarrow$ `ARUNACHAL PRADESH` origin
  4. `SIKKIM` destination $\leftarrow$ `ARUNACHAL PRADESH` origin
  5. `PUDUCHERRY` destination $\leftarrow$ `MIZORAM` origin

---

## 8. Cross-Table Mathematical Relationships in FY 2022–23

Running the 6 cross-table audits on FY 2022–23 reveals complete mathematical consistency:

| Audit Code | Description | FY 2022–23 Status | Observed Absolute Difference | Comparison with 2023–24 |
| :---: | :--- | :---: | :---: | :--- |
| **REC-DO01** | Table I matrix sum vs. Table II national total | **`PASS`** | $1.19 \times 10^{-7}$ Cr | Matches in both years |
| **REC-DO02** | Table III outward sum vs. Table IV inward total | **`PASS`** | $7.45 \times 10^{-9}$ Cr | Matches in both years |
| **REC-DO03** | National Total Partitioning (Out/In + Internal) | **`PASS`** | $1.49 \times 10^{-7}$ Cr | Matches in both years |
| **REC-DO04** | State Column Marginals (33 states) | **`PASS`** | $< 3.0 \times 10^{-8}$ Cr | Matches across all 33 in both years |
| **REC-DO05** | State Row Marginals (33 states) | **`PASS`** | $< 2.3 \times 10^{-8}$ Cr | Matches across all 33 in both years |
| **REC-DO06** | Table I Diagonal vs. Table V Internal (32 States) | **`PASS`** | $< 1.0 \times 10^{-8}$ Cr | Matches in both years |
| **REC-DO06** | Table I Diagonal vs. Table V Internal (`OTHER TERRITORY`) | **`PASS`** | **`6.98e-10 Cr` ($\approx 0.00$)** | **Diverges: 2022–23 matches; 2023–24 has ₹76,614.93 Cr diff** |

---

## 9. Comprehensive Classification of Differences

| Aspect | FY 2022–23 | FY 2023–24 | Classification | Governance Impact |
| :--- | :--- | :--- | :---: | :--- |
| **Worksheet Catalog** | 5 sheets | 5 sheets | **`COMPARABLE`** | Identical structure |
| **HS Chapter Set** | Chapters 10–99 (90) | Chapters 10–99 (90) | **`COMPARABLE`** | Identical structure |
| **Jurisdiction Set** | 33 entities | 33 entities | **`COMPARABLE`** | Identical geographic scope |
| **Jurisdiction Ordering** | Col D to AJ identical | Col D to AJ identical | **`COMPARABLE`** | Exact matching column alignments |
| **State Spelling (CG)** | `CHHATTISGARH` | `CHATTISGARH` | **`LABEL DIFFERENCE`** | Normalization map required |
| **State Spelling (JK)** | `JAMMU AND KASHMIR` | `JAMMU & KASHMIR` | **`LABEL DIFFERENCE`** | Normalization map required |
| **State Spelling (OT)** | `Other Territory` (Tab V) | `OTHER TERRITORY` | **`LABEL DIFFERENCE`** | Normalization map required |
| **Table III Col AK** | Present (`VALUE`) | Omitted / Absent | **`STRUCTURAL DIFFERENCE`** | Normalizer must support both |
| **Table I Null Count** | 2 cells | 5 cells | **`COMPARABLE`** | Sparsity within normal bounds |
| **OTHER TERRITORY Diagonal** | Exact match ($\Delta \approx 0$) | Discrepancy ($\Delta \approx ₹76,614.93$ Cr) | **`UNRESOLVED`** | Discrepancy unique to 2023–24 |

---

## 10. Comparability Assessment & Recommendations

### Feasibility of Using FY 2022–23 as Statistical Baseline
1. **Direct Comparability:** The two datasets **can be used as statistical baselines** provided that:
   - Canonical jurisdiction mapping resolves the three label differences (`CHHATTISGARH`, `JAMMU AND KASHMIR`, `Other Territory`).
   - The extraction layer handles Table III dynamically (extracting data columns D..AJ and ignoring or conditionally staging summary Column AK).
2. **Key Unresolved Discrepancy Finding:**
   - In FY 2022–23, `OTHER TERRITORY` diagonal in Table I ($₹333,390.86$ Cr) strictly matches Table V internal total ($₹333,390.86$ Cr).
   - In FY 2023–24, `OTHER TERRITORY` diagonal ($₹258,324.42$ Cr) diverges from Table V internal ($₹181,709.49$ Cr) by $+₹76,614.93$ Cr.
   - **Conclusion:** The ₹76,614.93 Crore discrepancy is **an idiosyncratic property of the FY 2023–24 workbook** and was not present in the historical baseline.
