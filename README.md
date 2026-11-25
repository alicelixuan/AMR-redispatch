# The congestion cost of electricity trade: Empirical evidence from German redispatch

The code and data in this repository replicate the analysis in

> Xu, A. L., 2026: The congestion cost of electricity trade: Empirical evidence from German redispatch.


## How to run

From the package folder, with Python 3.11 or newer:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python code/build/b3_jao_amr.py      # JAO AMR by TSO       -> data/analysis/amr_tso
python code/build/b5_merge_panel.py  # hourly analysis panel -> data/analysis/analysis_panel
python code/run_all.py               # all tables and figures -> output/
```

## Results

| Result | Script (`code/analysis/`) | Output |
|---|---|---|
| Table 2, Figure 4, Table 8 | `01_table2_table8_figure4.py` | `table2_main.tex`, `figure4_pds_path.png`, `table8_main_full.tex` |
| Table 3 | `02_table3_robustness.py` | `table3_robustness.tex` |
| Table 4 | `03_table4_by_year.py` | `table4_by_year.tex` |
| Table 5 | `04_table5_spillover.py` | `table5_spillover.tex` |
| Table 9 | `05_table9_direction.py` | `table9_direction.tex` |
| Tables 6 and 7 | `06_table6_table7_summary.py` | `table6_summary_by_tso.tex`, `table7_summary_candidates.tex` |
| Figure 5, annual cost totals (Sec. 6.3) | `07_figure5_cost.py` | `figure5_estimated_cost.png`, `cost_annual_totals.csv` |
| Figures 6, 7, 8, 9 | `08_figures6_to_9_appendix.py` | `figure6_average_minram.png`, `figure7_redispatch_by_tso.png`, `figure8_amr_by_tso.png`, `figure9_redispatch_direction_tech.png` |

Tables go to `output/tables/`, figures to `output/figures/`. Each figure's
plotted numbers are also saved as CSV in `output/tables/`.

## Data

### Files

| Location | File | Source |
|---|---|---|
| `data/raw/` | `de_lu_weather_data.csv`, `de_lu_radiation_data.csv` | NASA MERRA-2 (M2T1NXFLX): wind speed, temperature, solar irradiance |
| `data/raw/` | `actual_consumption_generation_control_area.pkl` | SMARD: load and generation by control area, 15-min |
| `data/raw/` | `installed_cap_filled.csv` | SMARD: installed capacity by control area |
| `data/raw/` | `load_neighbor_n_core_mid2022-2025.pkl`, `solar_windon_gen_neighbor.pkl` | ENTSO-E Transparency Platform: neighbour-zone load and generation |
| `data/raw/` | `kosten-pro-energiemenge.csv` | SMARD / BNetzA: monthly redispatch cost per MWh |
| `data/intermediate/` | `minRAM.pkl` | JAO Publication Tool: Core final computation, German base-case CNEs (also used directly for Figure 6) |
| `data/analysis/` | `redispatch_orders_15min.pkl` | Netztransparenz: redispatch orders, one row per active quarter-hour |

`b3` writes `data/analysis/amr_tso` and `b5` writes
`data/analysis/analysis_panel`, the estimation sample.

### Rebuilding from the original downloads (optional)

| Script (`code/build/`) | Does |
|---|---|
| `b1_redispatch_timeseries.py` | `data/raw/Redispatch_Daten.csv` (Netztransparenz export) → `redispatch_orders_15min` |
| `b2_jao_download.py` | downloads JAO final-computation files to `data/raw/final_computation_<year>/` |
| `b3_jao_amr.py` | uses `data/intermediate/minRAM.pkl` if present, otherwise the `b2` downloads |
| `b4_entsoe_download.py` | downloads the two ENTSO-E files; needs `ENTSOE_API_KEY` in the environment |
| `b5_merge_panel.py` | merges everything into the hourly panel |

The MERRA-2 and SMARD extracts were prepared outside this package and are
provided as source extracts.

### Availability

All data are public: JAO Publication Tool (publicationtool.jao.eu),
Netztransparenz (netztransparenz.de), SMARD / Bundesnetzagentur (smard.de),
ENTSO-E Transparency Platform (transparency.entsoe.eu; free registration for
API access), NASA MERRA-2 (data.nasa.gov). Full citations are in the paper.
Check each provider's terms of use before redistributing the extracts.

