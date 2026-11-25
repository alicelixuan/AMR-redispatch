"""Shared access to the main specification's PDS-selected controls.

code/analysis/01_table2_table8_figure4.py runs the selection and stores it in
output/intermediate/pds_selection.json. Every later script reads that file,
so all tables use exactly the same control set. If it is missing (a script
run on its own), the selection is re-run.
"""
from __future__ import annotations

import config as C
from lib.io import load_json, save_json

SEL_PATH = C.OUT_INTERMEDIATE / "pds_selection.json"
EST_PATH = C.OUT_INTERMEDIATE / "main_estimates.json"


def main_controls(panel=None) -> list[str]:
    if SEL_PATH.exists():
        sel = load_json(SEL_PATH)["S_pds_1se"]
    else:
        print("[main_spec] no stored PDS selection -> running PDS now")
        from lib.pds import run_pds
        from lib.panel import load_panel
        out, _ = run_pds(panel if panel is not None else load_panel())
        save_json(out, SEL_PATH)
        sel = out["S_pds_1se"]
    if sorted(sel) != sorted(C.PAPER_PDS_1SE):
        print(f"[main_spec] WARNING: 1-SE selection {sel} differs from the "
              f"paper's {C.PAPER_PDS_1SE}")
    return list(sel)
