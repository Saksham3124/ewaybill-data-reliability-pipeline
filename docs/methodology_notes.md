# Official Methodology & Source Governance Notes

**Target Dataset:** `data/Road_EwayBill_2023_24.xlsx`  
**Issuing Agency:** Directorate General of Commercial Intelligence and Statistics (DGCI&S), Ministry of Commerce and Industry, Government of India, Kolkata  
**Administrative Context:** Domestic Goods Movement under the Goods and Services Tax (GST) E-Way Bill System  
**Reporting Period:** Financial Year 2023–24 (April 1, 2023 – March 31, 2024)  
**Mode of Transport:** Road Freight Only  
**Governance Standard:** Strict distinction between (1) Documented by Official Source, (2) Observed from Data, and (3) Inference / Hypothesis.

---

## 1. Governance Classification Framework

To ensure that assumptions are never conflated with authoritative facts, all information in this project is classified under three rigorous epistemic tiers:

```
[DOCUMENTED BY OFFICIAL SOURCE]
  Explicitly stated in the workbook's text, title rows, headers, or official DGCI&S publications.
       │
       ▼
[OBSERVED FROM DATA]
  Mathematically or structurally verified across cells, but lacking explicit explanatory text in the source.
       │
       ▼
[INFERENCE / HYPOTHESIS]
  Plausible domain or economic interpretation requiring confirmation from the issuing authority before adoption.
```

---

## 2. Table-by-Table Source Documentation & Evidence

### Table I: `Tab I_Stat_to_Stat_Revised_Road`

- **[DOCUMENTED BY OFFICIAL SOURCE] Table Title:**  
  `"Table I : State wise Movement of Goods by Road during 2023 - 24 (Value in INR Crore)"` (Cell `B1:N1`).
- **[DOCUMENTED BY OFFICIAL SOURCE] Layout & Dimensions:**  
  - Row 2: `"From State ---->>"`, followed by 33 geographic entities in Columns C to AI.
  - Row 3: `"To State ---->>"`, with vertical merged headers `C2:C3` to `AI2:AI3`.
  - Column B (Rows 4–36): 33 geographic entities identical to the column list.
  - Active Data Bounding Box: Rows 4 to 36, Columns C to AI ($33 \times 33 = 1,089$ cells).
- **[DOCUMENTED BY OFFICIAL SOURCE] Footnotes, Totals, or Rules:**  
  **None.** There is no total row, no total column, and no footnote in the sheet.
- **[OBSERVED FROM DATA] Matrix Sum:**  
  The sum of all numeric cells in Table I equals **₹20,319,786.98011017 Crore**.
- **[OBSERVED FROM DATA] Marginal Sums:**  
  - Column sum for state $j$ equals the sum of Table III (Outward) Col $j$ + Table V (Internal) Col $j$.
  - Row sum for state $i$ equals the sum of Table IV (Inward) Col $i$ + Table V (Internal) Col $i$.
- **[INFERENCE / HYPOTHESIS] Semantics:**  
  Columns represent the origin of dispatch ("From State") and rows represent the destination of receipt ("To State"). The diagonal elements represent intra-state movement.

---

### Table II: `Tab II_Chap_Revised_Road`

- **[DOCUMENTED BY OFFICIAL SOURCE] Table Title:**  
  `"Table II:Chapter wise Movement of Goods by Road during 2023 - 24 (Value in INR Crore)"` (Cell `B1:E1`).
- **[DOCUMENTED BY OFFICIAL SOURCE] Headers & Fields:**  
  - Column B: `"CHAPTER CODE"` (Two-digit string `'10'` to `'99'`).
  - Column C: `"CHAPTER DESCRIPTION"` (Commodity description).
  - Column D: `"VALUE (in INR Crore)"`.
- **[DOCUMENTED BY OFFICIAL SOURCE] Reported Total:**  
  Row 93, Cells `B93:C93` merged: `"TOTAL VALUE (in INR Crore)---->>"`. Cell `D93`: `20319786.98011017`.
- **[OBSERVED FROM DATA] Completeness:**  
  90 data rows (Rows 3 to 92). Sum of individual rows $\sum_{r=3}^{92} D_r = 20,319,786.98011017$ Crore (difference vs. `D93` $= 0.0$).
- **[DOCUMENTED BY OFFICIAL SOURCE] Relationship to Other Tables:**  
  **None stated.** The table does not state whether this value is inter-state only, internal only, or composite.

---

### Table III: `Tab III_Outward_Revised_Road`

- **[DOCUMENTED BY OFFICIAL SOURCE] Table Title:**  
  `"Table III:Chapter wise Outward Movement of Goods by Road during 2023 - 24 (Value in INR Crore)"` (Cell `B1:M1`).
- **[DOCUMENTED BY OFFICIAL SOURCE] Headers & Fields:**  
  - Column B: `"CHAPTER CODE"`.
  - Column C: `"CHAPTER DESCRIPTION"`.
  - Columns D to AJ: 33 State/UT names.
- **[DOCUMENTED BY OFFICIAL SOURCE] Reported Totals:**  
  Row 93, Cells `B93:C93` merged: `"OUTWARD VALUE (in INR Crore) ----->>"`, followed by 33 state outward totals in Columns D to AJ.
- **[DOCUMENTED BY OFFICIAL SOURCE] Total Column:**  
  **Omitted.** Table III does **not** contain a row-level `TOTAL` column summarizing chapters across states.
- **[OBSERVED FROM DATA] Computed Sums:**  
  Sum of all 33 state column totals $= \mathbf{10,429,324.404046647\text{ Crore}}$.
  Sum of all individual matrix cells $= \mathbf{10,429,324.404046647\text{ Crore}}$.
- **[INFERENCE / HYPOTHESIS] Meaning of Outward Movement:**  
  Represents goods dispatched by road from the specified origin state to destinations outside that state (inter-state outward dispatches).

---

### Table IV: `Tab IV_Inward_Revised_Road`

- **[DOCUMENTED BY OFFICIAL SOURCE] Table Title:**  
  `"Table IV:Chapter wise Inward Movement of Goods by Road during 2023 - 24 (Value in INR Crore)"` (Cell `B1`).
- **[DOCUMENTED BY OFFICIAL SOURCE] Headers & Fields:**  
  - Column B: `"CHAPTER CODE"`.
  - Column C: `"CHAPTER DESCRIPTION"`.
  - Columns D to AJ: 33 State/UT names.
  - Column AK: `"TOTAL"`.
- **[DOCUMENTED BY OFFICIAL SOURCE] Reported Totals:**  
  - Row 93, Cells `B93:C93` merged: `"INWARD VALUE (in INR Crore) ----->>"`, followed by 33 state inward totals in Columns D to AJ.
  - Cell `AK93`: Grand Total `= 10429324.40404665` Crore.
- **[OBSERVED FROM DATA] Computed Sums & Balance:**  
  - Sum of all 33 state column totals $= \mathbf{10,429,324.404046647\text{ Crore}}$.
  - Matches Cell `AK93` within $3.72 \times 10^{-9}$ Crore.
  - **National Outward vs. National Inward:**  
    $\sum \text{Outward (Table III)} - \sum \text{Inward (Table IV)} = \mathbf{0.000000000\text{ Crore}}$.
- **[INFERENCE / HYPOTHESIS] Meaning of Inward Movement:**  
  Represents goods received by road in the specified destination state from origins outside that state (inter-state inward receipts).

---

### Table V: `Tab V_Internal_Revised_Road`

- **[DOCUMENTED BY OFFICIAL SOURCE] Table Title:**  
  `"Table V:Chapter wise Internal Movement of Goods by Road during 2023 - 24 (Value in INR Crore)"` (Cell `B1`).
- **[DOCUMENTED BY OFFICIAL SOURCE] Headers & Fields:**  
  - Column B: `"CHAPTER CODE"`.
  - Column C: `"CHAPTER DESCRIPTION"`.
  - Columns D to AJ: 33 State/UT names.
  - Column AK: `"TOTAL"`.
- **[DOCUMENTED BY OFFICIAL SOURCE] Reported Totals:**  
  - Row 93, Cells `B93:C93` merged: `"INTERNAL VALUE (in INR Crore) ----->>"`, followed by 33 state internal totals in Columns D to AJ.
  - Cell `AK93`: Grand Total `= 9890462.576063517` Crore.
- **[OBSERVED FROM DATA] Computed Sums:**  
  Sum of all 33 state column totals $= \mathbf{9,890,462.576063516\text{ Crore}}$.
- **[INFERENCE / HYPOTHESIS] Meaning of Internal Movement:**  
  Represents intra-state goods movement by road where the consignment originates and terminates within the same State/UT.

---

## 3. Geographic Coverage & Jurisdiction Analysis

### 3.1 Documented Entities
The workbook consistently features exactly 33 geographic entities in identical order across all five tables:

| # | Entity Name in Source | Official Political Classification | Discrepancy / Observation |
| :-: | :--- | :--- | :--- |
| 1–5 | ANDHRA PRADESH, ARUNACHAL PRADESH, ASSAM, BIHAR, CHANDIGARH | 4 States, 1 UT | Standard naming. |
| 6 | `CHATTISGARH` | State | **[DOCUMENTED BY OFFICIAL SOURCE / DATA]** Spelled with a single "H" instead of official `CHHATTISGARH`. |
| 7–11 | DELHI, GOA, GUJARAT, HARYANA, HIMACHAL PRADESH | 4 States, 1 UT | Standard naming. |
| 12 | `JAMMU & KASHMIR` | Union Territory | Covers J&K UT; Ladakh status not specified. |
| 13–22 | JHARKHAND, KARNATAKA, KERALA, MADHYA PRADESH, MAHARASHTRA, MANIPUR, MEGHALAYA, MIZORAM, NAGALAND, ODISHA | 10 States | Standard naming. |
| 23 | `OTHER TERRITORY` | Special Tax Jurisdiction | **[DOCUMENTED BY OFFICIAL SOURCE]** Listed as a discrete jurisdiction with no explanatory note in workbook. |
| 24 | `PUDUCHERRY` | Union Territory | Standard naming. |
| 25–33 | PUNJAB, RAJASTHAN, SIKKIM, TAMIL NADU, TELANGANA, TRIPURA, UTTAR PRADESH, UTTARAKHAND, WEST BENGAL | 9 States | Standard naming. |

### 3.2 Omissions & Exclusions
- **[DOCUMENTED BY OFFICIAL SOURCE] Stated Exclusions:** **None.** The workbook contains no preface, footnotes, or text explaining why certain administrative units are absent.
- **[OBSERVED FROM DATA] Missing Administrative Entities:**
  1. `ANDAMAN & NICOBAR ISLANDS` (UT) — Absent.
  2. `LAKSHADWEEP` (UT) — Absent.
  3. `LADAKH` (UT) — Absent.
  4. `DADRA & NAGAR HAVELI AND DAMAN & DIU` (UT) — Absent.
- **[INFERENCE / HYPOTHESIS] Reason for Absence:**
  - Andaman & Nicobar and Lakshadweep are islands with no road connectivity to mainland India.
  - Ladakh movements may be aggregated under Jammu & Kashmir or Other Territory.
  - Dadra & Nagar Haveli and Daman & Diu may be subsumed within Gujarat/Maharashtra or Other Territory.

### 3.3 Meaning of "OTHER TERRITORY"
- **[DOCUMENTED BY OFFICIAL SOURCE] In Workbook:** No definition or explanation is provided.
- **[DOCUMENTED BY OFFICIAL SOURCE] In GST Law:** Under Section 2(81) of the Central Goods and Services Tax (CGST) Act, 2017:
  > *"other territory includes territories other than those comprising in a State and those referred to in sub-clauses (a) to (e) of clause (114)"* (i.e. the Exclusive Economic Zone, continental shelf, and territorial waters beyond 12 nautical miles).
- **[INFERENCE / HYPOTHESIS]:** Transactions mapped to `OTHER TERRITORY` in E-Way bill generation represent offshore installations (such as offshore petroleum platforms), high seas dispatches, or special economic zones lacking state assignment.

---

## 4. Commodity Coverage, Exclusions & Data Precision

### 4.1 Commodity Coverage
- **[DOCUMENTED BY OFFICIAL SOURCE] Chapter Codes:** Codes span sequentially from `'10'` to `'99'` across 90 chapters.
- **[DOCUMENTED BY OFFICIAL SOURCE] Stated Exclusions:** **None.** The workbook does not mention why Chapters 01 to 09 are absent.
- **[OBSERVED FROM DATA] Missing Chapters:**
  Chapters 01, 02, 03, 04, 05, 06, 07, 08, and 09 are completely absent from all tables.
- **[INFERENCE / HYPOTHESIS] Exemption Rationale:**
  Under Rule 138(14) of the CGST Rules, 2017 (read with Annexure / Notification No. 27/2017-Central Tax), unprocessed agricultural and livestock commodities (live animals, fresh meat, fish, milk, vegetables, fresh fruits) are statutorily exempt from E-Way bill generation.
- **[OBSERVED FROM DATA] Chapter 77:**
  Labeled `"RESERVED FOR POSSIBE FUTURE USE"`. Populated with ₹0.74 Crore in Table V and ₹0.00 in others.
- **[OBSERVED FROM DATA] Lexical Typographical Errors:**
  Source commodity descriptions contain typos: Chapter 16 (`MOLLUSES`), Chapter 19 (`MIILK`, `PASTRY COOK' PRODUCTS`), Chapter 36 (`CERTAN COMBUSTIBLES PREPARATIONS`), Chapter 41 (`OTHER THEN FURSKINS`), Chapter 77 (`POSSIBE`), Chapter 90 (`MEASUREING`).

### 4.2 Monetary Units & Numeric Precision
- **[DOCUMENTED BY OFFICIAL SOURCE] Unit:** `"Value in INR Crore"` stated in title row of all five tables ($1\text{ Crore} = 10^7\text{ INR}$).
- **[OBSERVED FROM DATA] Precision:** Numbers are stored as 64-bit IEEE 754 floating-point values with up to 12 decimal places (fractional precision down to sub-paisa resolution: $10^{-9}\text{ Crore} = 1\text{ Paisa}$).
- **[OBSERVED FROM DATA] Blank Cells:**
  - Empty cells are stored as `None` (openpyxl `NoneType`).
  - Blank count: Table I (5), Table II (0), Table III (108), Table IV (27), Table V (164).
  - When blank cells are evaluated as zero ($0.0$), all published column and row totals balance with precision $\le 10^{-9}$.

---

## 5. Examination of Profiling Observations

### 5.1 Observation 1: For 32 of 33 Jurisdictions, Table I Diagonal = Table V Internal Total
- **Classification:** **[OBSERVED FROM DATA]**
- **Data Evidence:**
  For every State/UT $k \in \{1 \dots 33\} \setminus \{\text{OTHER TERRITORY}\}$:
  $$|S_1[k, k] - S_5[\text{TOTAL}, k]| = 0.000000000000$$
- **Official Documentation:** **None.** The source workbook does not state that Table I's diagonal represents internal movement, nor that it must equal Table V.

---

### 5.2 Observation 2: For OTHER TERRITORY, Table I Diagonal Diverges by ₹76,614.93 Crore
- **Classification:** **[OBSERVED FROM DATA] — UNRESOLVED DATA/DEFINITION DIFFERENCE**
- **Data Evidence:**
  - Table I Diagonal (`OTHER TERRITORY -> OTHER TERRITORY`): **₹258,324.421758 Crore**
  - Table V Internal Total (`Row 93, Col OTHER TERRITORY`): **₹181,709.488219 Crore**
  - Numerical Difference: **$+₹76,614.933539\text{ Crore}$**
- **Official Source Explanation:** **NONE.**
- **Project Documentation Requirement:**  
  Because the official methodology contains no explanation for this divergence:
  > **"UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION"**
  
  *No explanatory hypothesis may be assumed as factual in reconciliation rules.*

---

### 5.3 Observation 3: National Total Movement = ₹20,319,786.98 Crore
- **Classification:** **[DOCUMENTED BY OFFICIAL SOURCE / OBSERVED FROM DATA]**
- **Data Evidence:**
  - Published in Table II Row 93 Cell `D93`: `20319786.98011017`.
  - Recomputed sum of Table II data rows (Rows 3–92): `20319786.98011017`.
  - Sum of all cells in Table I matrix: `20319786.98011017`.

---

### 5.4 Observations 4 & 5: National Outward = National Inward = ₹10,429,324.40 Crore
- **Classification:** **[OBSERVED FROM DATA]**
- **Data Evidence:**
  - Sum of Table III Outward state totals (Row 93, Cols D–AJ): **₹10,429,324.404046647 Crore**.
  - Published Table IV Inward Grand Total (Cell `AK93`): **₹10,429,324.40404665 Crore**.
  - Difference: **0.000000000000 Crore** (within floating-point rounding: $3.72 \times 10^{-9}$).
- **Official Documentation:** **None.** The source does not explicitly articulate the macroeconomic identity that national outward must equal national inward.

---

### 5.5 Observations 6 & 7: Table I Total and Table II Total Agree with National Total
- **Classification:** **[OBSERVED FROM DATA]**
- **Data Evidence:**
  $$\sum \text{Table I Matrix} = \text{Table II Reported Total} = 20,319,786.98011017 \text{ Crore}$$
  Difference: **0.000000000000 Crore**.

---

### 5.6 Observation 8: OTHER TERRITORY Marginal Conservation Remains Consistent
- **Classification:** **[OBSERVED FROM DATA]**
- **Data Evidence:**
  Even though the diagonal element diverges by ₹76,614.93 Crore:
  1. Column Marginal Conservation:
     $$\sum_{r=4}^{36} S_1[r, \text{OTHER TERRITORY}] = 1,942,706.143386\text{ Crore}$$
     $$\text{Table III Total} + \text{Table V Total} = 1,760,996.655167 + 181,709.488219 = 1,942,706.143386\text{ Crore}$$
     $$\Delta = 0.000000000\text{ Crore}$$
  2. Row Marginal Conservation:
     $$\sum_{c=3}^{35} S_1[\text{OTHER TERRITORY}, c] = 1,624,743.517600\text{ Crore}$$
     $$\text{Table IV Total} + \text{Table V Total} = 1,443,034.029381 + 181,709.488219 = 1,624,743.517600\text{ Crore}$$
     $$\Delta = 0.000000000\text{ Crore}$$
- **Official Source Explanation:** **NONE.**
- **Status:** **UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION.**
