"""
scripts/profile_historical_workbook.py
--------------------------------------
Profiles data/Road_EwayBill_2022_23.xlsx and compares it against
data/Road_EwayBill_2023_24.xlsx across all structural dimensions.
Outputs full JSON analysis for generating docs/historical_source_profile.md.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
import openpyxl
import pandas as pd


def get_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def profile_single_workbook(filepath: str) -> dict:
    p = Path(filepath)
    stat = p.stat()
    sha256 = get_sha256(filepath)

    wb_raw = openpyxl.load_workbook(str(p), data_only=False, read_only=False)
    wb_data = openpyxl.load_workbook(str(p), data_only=True, read_only=False)

    profile = {
        "filename": p.name,
        "filepath": str(p.resolve()),
        "size_bytes": stat.st_size,
        "sha256": sha256,
        "sheet_names": wb_raw.sheetnames,
        "sheets": {}
    }

    for name in wb_raw.sheetnames:
        ws_r = wb_raw[name]
        ws_d = wb_data[name]

        # Scan active rows and columns
        non_empty_rows = set()
        non_empty_cols = set()
        formulas = []
        null_cells = 0
        merged_ranges = [str(m) for m in ws_r.merged_cells.ranges]

        # Find bounds
        for r in range(1, ws_r.max_row + 1):
            for c in range(1, ws_r.max_column + 1):
                raw_val = ws_r.cell(r, c).value
                data_val = ws_d.cell(r, c).value
                if raw_val is not None:
                    non_empty_rows.add(r)
                    non_empty_cols.add(c)
                    if isinstance(raw_val, str) and raw_val.startswith("="):
                        formulas.append({"cell": f"{openpyxl.utils.get_column_letter(c)}{r}", "formula": raw_val})

        min_r = min(non_empty_rows) if non_empty_rows else 0
        max_r = max(non_empty_rows) if non_empty_rows else 0
        min_c = min(non_empty_cols) if non_empty_cols else 0
        max_c = max(non_empty_cols) if non_empty_cols else 0

        # Read title, header, and metadata
        title_val = ws_d.cell(1, 1).value
        header_vals = {}
        for r in range(min_r, min(min_r + 4, max_r + 1)):
            row_vals = [ws_d.cell(r, c).value for c in range(min_c, max_c + 1)]
            header_vals[f"row_{r}"] = [str(v) if v is not None else "" for v in row_vals]

        sheet_info = {
            "declared_max_row": ws_r.max_row,
            "declared_max_col": ws_r.max_column,
            "active_min_row": min_r,
            "active_max_row": max_r,
            "active_min_col": min_c,
            "active_max_col": max_c,
            "active_row_count": (max_r - min_r + 1) if non_empty_rows else 0,
            "active_col_count": (max_c - min_c + 1) if non_empty_cols else 0,
            "title_cell_A1": title_val,
            "header_rows_sample": header_vals,
            "merged_cells_count": len(merged_ranges),
            "merged_ranges": merged_ranges,
            "formula_count": len(formulas),
            "formulas_sample": formulas[:10]
        }

        # Specific extraction depending on sheet structure
        if "Stat_to_Stat" in name:
            # Sheet 1
            # Column headers at row 3 (cols 3 to 35)
            origin_states = [ws_d.cell(3, c).value for c in range(3, 36)]
            dest_states = [ws_d.cell(r, 2).value for r in range(4, 37)]
            # check null count in matrix (rows 4 to 36, cols 3 to 35)
            mat_nulls = sum(1 for r in range(4, 37) for c in range(3, 36) if ws_d.cell(r, c).value is None)
            sheet_info["entity_details"] = {
                "origin_states": origin_states,
                "dest_states": dest_states,
                "matrix_rows": len(dest_states),
                "matrix_cols": len(origin_states),
                "matrix_null_cells": mat_nulls
            }
        elif "Chap_Revised" in name:
            # Sheet 2
            chapters = []
            for r in range(3, 93):
                code = ws_d.cell(r, 2).value
                desc = ws_d.cell(r, 3).value
                val = ws_d.cell(r, 4).value
                chapters.append({"row": r, "code": str(code) if code is not None else None, "desc": desc, "val": val})
            reported_total_r93 = ws_d.cell(93, 4).value
            sheet_info["entity_details"] = {
                "chapters_count": len(chapters),
                "chapter_codes": [c["code"] for c in chapters],
                "chapter_descriptions": {c["code"]: c["desc"] for c in chapters},
                "reported_total_row_93": reported_total_r93,
                "null_values_count": sum(1 for c in chapters if c["val"] is None)
            }
        elif "Outward" in name:
            # Sheet 3
            states = [ws_d.cell(2, c).value for c in range(4, 37)]
            chapters = []
            nulls = 0
            for r in range(3, 93):
                code = ws_d.cell(r, 2).value
                desc = ws_d.cell(r, 3).value
                chapters.append({"code": str(code) if code is not None else None, "desc": desc})
                for c in range(4, 37):
                    if ws_d.cell(r, c).value is None:
                        nulls += 1
            col_ak_present = (ws_d.cell(2, 37).value is not None or ws_d.cell(3, 37).value is not None)
            row_93_totals = {states[i]: ws_d.cell(93, 4 + i).value for i in range(len(states))}
            sheet_info["entity_details"] = {
                "states": states,
                "chapters_count": len(chapters),
                "chapter_codes": [c["code"] for c in chapters],
                "null_cells_in_data": nulls,
                "col_ak_total_present": col_ak_present,
                "row_93_state_totals": row_93_totals
            }
        elif "Inward" in name:
            # Sheet 4
            states = [ws_d.cell(2, c).value for c in range(4, 37)]
            chapters = []
            nulls = 0
            for r in range(3, 93):
                code = ws_d.cell(r, 2).value
                desc = ws_d.cell(r, 3).value
                chapters.append({"code": str(code) if code is not None else None, "desc": desc})
                for c in range(4, 37):
                    if ws_d.cell(r, c).value is None:
                        nulls += 1
            col_ak_name = ws_d.cell(2, 37).value
            grand_total_ak93 = ws_d.cell(93, 37).value
            row_93_totals = {states[i]: ws_d.cell(93, 4 + i).value for i in range(len(states))}
            sheet_info["entity_details"] = {
                "states": states,
                "chapters_count": len(chapters),
                "chapter_codes": [c["code"] for c in chapters],
                "null_cells_in_data": nulls,
                "col_ak_header": str(col_ak_name),
                "grand_total_cell_ak93": grand_total_ak93,
                "row_93_state_totals": row_93_totals
            }
        elif "Internal" in name:
            # Sheet 5
            states = [ws_d.cell(2, c).value for c in range(4, 37)]
            chapters = []
            nulls = 0
            for r in range(3, 93):
                code = ws_d.cell(r, 2).value
                desc = ws_d.cell(r, 3).value
                chapters.append({"code": str(code) if code is not None else None, "desc": desc})
                for c in range(4, 37):
                    if ws_d.cell(r, c).value is None:
                        nulls += 1
            col_ak_name = ws_d.cell(2, 37).value
            grand_total_ak93 = ws_d.cell(93, 37).value
            row_93_totals = {states[i]: ws_d.cell(93, 4 + i).value for i in range(len(states))}
            sheet_info["entity_details"] = {
                "states": states,
                "chapters_count": len(chapters),
                "chapter_codes": [c["code"] for c in chapters],
                "null_cells_in_data": nulls,
                "col_ak_header": str(col_ak_name),
                "grand_total_cell_ak93": grand_total_ak93,
                "row_93_state_totals": row_93_totals
            }

        profile["sheets"][name] = sheet_info

    wb_raw.close()
    wb_data.close()
    return profile


def main():
    f22_23 = "data/Road_EwayBill_2022_23.xlsx"
    f23_24 = "data/Road_EwayBill_2023_24.xlsx"

    print("Profiling FY 2022-23...")
    prof_22 = profile_single_workbook(f22_23)
    print("Profiling FY 2023-24...")
    prof_24 = profile_single_workbook(f23_24)

    output = {
        "prof_2022_23": prof_22,
        "prof_2023_24": prof_24
    }

    out_file = "scratch_historical_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Profiling complete. JSON written to {out_file}")


if __name__ == "__main__":
    main()
