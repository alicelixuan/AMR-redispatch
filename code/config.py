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
OUT_LOGS = OUT / "logs"

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
# Published values, used only to print a paper-vs-replication check
# (output/logs/replication_check.csv). They play no role in estimation.
# ---------------------------------------------------------------------------
PAPER_PDS_1SE = ["wind_onsh_DK_1", "wind_onsh_DK_2", "wind_onsh_PL"]
PAPER_PDS_MIN_K = 51

PAPER = {
    "T2 (1) AMR coef": 0.279, "T2 (1) AMR se": 0.039, "T2 (1) within R2": 0.272,
    "T2 (1) IQR effect MW": 115.3,
    "T2 (2) AMR coef": 0.199, "T2 (2) AMR se": 0.034, "T2 (2) within R2": 0.408,
    "T2 (2) IQR effect MW": 82.3, "T2 N": 123689, "AMR IQR MW": 414,
    "T3 [1] activation": 51.649, "T3 [1] intensity": 0.192,
    "T3 [2] intensity": 0.170, "T3 [2] N": 65324,
    "T3 [3] activation": 0.092, "T3 [3] intensity": 0.000008,
    "T3 [4] activation": 65.356, "T3 [4] intensity": 0.166, "T3 [4] N": 64412,
    "T4 2022 coef": 0.372, "T4 2023 coef": 0.280, "T4 2024 coef": 0.180,
    "T4 2025 coef": 0.289,
    "T4 2022 se": 0.264, "T4 2023 se": 0.079, "T4 2024 se": 0.048,
    "T4 2025 se": 0.040,
    "T5 (2) AMR": 0.157, "T5 (3) AMR": 0.178, "T5 (3) other sum": 0.022,
    "T9 up AMR": 0.012, "T9 down AMR": 0.187,
    "Cost 2023 MEUR": 305, "Cost 2024 MEUR": 577, "Cost 2025 MEUR": 925,
}
