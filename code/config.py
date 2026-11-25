"""
Central configuration for the replication package.

Every path, column name and estimation constant used by more than one script
lives here, so a reader can audit the specification in one place.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CODE = Path(__file__).resolve().parent          # .../code
ROOT = CODE.parent                               # project root: data/, code/, output/

DATA_RAW = ROOT / "data" / "raw"                  # source extracts as downloaded
DATA_INTERMEDIATE = ROOT / "data" / "intermediate"  # built by code/build/ scripts
DATA_ANALYSIS = ROOT / "data" / "analysis"        # inputs to code/analysis/ scripts

OUT = ROOT / "output"
OUT_TABLES = OUT / "tables"
OUT_FIGURES = OUT / "figures"
OUT_INTERMEDIATE = OUT / "intermediate"           # estimates passed between scripts

# Analysis inputs. Stems only: lib.io.read_any() accepts .parquet, .pkl or .csv.
PANEL_FILE = DATA_ANALYSIS / "analysis_panel"        # hourly (DateTime, TSO) panel, cleaned
AMR_TSO_FILE = DATA_ANALYSIS / "amr_tso"             # JAO base-case AMR summed by (DateTime, TSO)
REDISPATCH_TS_FILE = DATA_ANALYSIS / "redispatch_orders_15min"  # Netztransparenz orders, 15-min rows
COST_FILE = DATA_RAW / "kosten-pro-energiemenge.csv"  # SMARD redispatch cost per MWh, monthly
MINRAM_FILE = DATA_INTERMEDIATE / "minRAM"           # JAO base-case CNEs x hour (Figure 6)

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
Y_COL = "redispatch_mw"
Y_UP = "redispatch_up_mw"
Y_DOWN = "redispatch_down_mw"
D_COL = "Amr"
LOAD_COL = "grid load MW consumption"

BASELINE_CONTROLS = [
    LOAD_COL,
    "wind_onsh_potential",
    "wind_off_potential",
]

# The 54 neighbour-zone candidate controls entering post-double selection
# (Section 5.2). Order matters: it fixes the column order of the LASSO design
# and therefore the tie-breaking in the entry-order ranking for Figure 4.
CANDIDATES = [
    "Load_AT", "Load_BE", "Load_CH", "Load_CZ", "Load_DK_1", "Load_DK_2",
    "Load_FR", "Load_HR", "Load_HU", "Load_NL", "Load_PL", "Load_RO",
    "Load_SI", "Load_SK", "Load_NO_1", "Load_NO_2", "Load_NO_3", "Load_NO_4",
    "Load_NO_5", "solar_AT", "wind_onsh_AT", "solar_BE", "wind_onsh_BE",
    "solar_CH", "wind_onsh_CH", "solar_CZ", "wind_onsh_CZ", "solar_DK_1",
    "wind_onsh_DK_1", "solar_DK_2", "wind_onsh_DK_2", "solar_FR",
    "solar_HR", "wind_onsh_HR", "solar_HU", "wind_onsh_HU", "solar_NL",
    "wind_onsh_NL", "solar_PL", "wind_onsh_PL", "solar_RO", "wind_onsh_RO",
    "solar_SI", "wind_onsh_SI", "solar_SK", "solar_NO_1", "wind_onsh_NO_1",
    "wind_onsh_NO_3", "wind_onsh_NO_4", "wind_off_DK_1", "wind_off_DK_2",
    "wind_off_NL", "wind_off_NO_2", "hydro_res_FR",
]

TSOS = ["50Hertz", "Amprion", "TenneT DE", "TransnetBW"]
TSO_COLORS = ["#ec8831", "#84187d", "#52a8e6", "#57a517"]

OTHER_AMR_COLS = [f"other_AMR_{t}" for t in TSOS]
OTHER_AMR_SUM = "other_AMR_sum"

# ---------------------------------------------------------------------------
# Estimation constants
# ---------------------------------------------------------------------------
DK_KERNEL = "bartlett"
DK_BANDWIDTH = 336          # Driscoll-Kraay bandwidth in hours (two weeks)

PDS_N_SPLITS = 5            # time-blocked CV folds
PDS_N_ALPHAS = 100          # LassoCV penalty grid
PDS_MAX_ITER = 20000
PDS_RANDOM_STATE = 123
PDS_COEF_TOL = 1e-10        # |coef| above this counts as selected
ENTRY_N_ALPHAS = 150        # lasso_path grid used to order controls for Figure 4

# Figure 4: k values that get a marker (as in the published figure)
FIG4_MARKER_KS = [0, 1, 2, 3, 5, 8, 10, 12, 14, 19, 20, 24, 30, 40, 51, 54]
FIG4_YLIM = (-0.01, 0.39)

# Figure 5: the published cost estimate multiplies by the AMR coefficient
# rounded to three decimals (0.199). Set to None to use the unrounded estimate.
COST_BETA_DECIMALS = 3

# How quarter-hourly series (redispatch, SMARD load/generation, ENTSO-E load)
# are brought to the hourly panel in code/build/b5_merge_panel.py:
#   "top_of_hour" the hourly JAO time stamps are left-joined with the
#                 quarter-hourly series, so each hour carries the value of its
#                 first quarter-hour. This reproduces the paper.
#   "mean"        hourly mean of all four quarter-hours (redispatch = MWh in
#                 the hour). Alternative; changes the PDS 1-SE selection.
HOURLY_AGGREGATION = "top_of_hour"

# Sample window of the hourly panel (UTC), as in the merge notebook.
SAMPLE_START = "2022-06-08 22:00:00+00:00"
SAMPLE_END_EXCL = "2026-01-01 00:00:00+00:00"

# ---------------------------------------------------------------------------
# The three controls selected in the paper. Used only to word the note under
# Table 2; it plays no role in estimation.
# ---------------------------------------------------------------------------
PAPER_PDS_1SE = ["wind_onsh_DK_1", "wind_onsh_DK_2", "wind_onsh_PL"]
