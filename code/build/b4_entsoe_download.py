"""
BUILD STEP 4 - ENTSO-E neighbour-zone load and renewable generation

    ENTSOE_API_KEY=<your key> python code/build/b4_entsoe_download.py

Outputs (data/raw/):
    load_neighbor_n_core_mid2022-2025.pkl   columns Load_<zone>
    solar_windon_gen_neighbor.pkl           columns solar_<zone>, wind_onsh_<zone>,
                                            wind_off_<zone>, hydro_res_FR

Source: notebook "5 - Trade_on_redispatch.ipynb", cells 2-7.

NOTE: the original solar_windon_gen_neighbor.pkl was assembled over several
interactive runs (France separately because of its column structure). This
script issues the same queries in one pass; check its column set against the
candidate list in config.CANDIDATES. Requires a personal ENTSO-E
Transparency Platform API key; never commit the key to the package.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config as C  # noqa: E402

START = pd.Timestamp("20220601 00:00:00", tz="UTC")
END = pd.Timestamp("20260101 01:00:00", tz="UTC")

LOAD_ZONES = ["DE_LU", "AT", "BE", "CH", "CZ", "DK_1", "DK_2", "FR", "HR", "HU",
              "NL", "PL", "RO", "SI", "SK", "NO_1", "NO_2", "NO_3", "NO_4", "NO_5"]
VRE_ZONES = ["AT", "BE", "CH", "CZ", "DK_1", "DK_2", "FR", "HR", "HU", "NL", "PL",
             "RO", "SI", "SK", "NO_1", "NO_2", "NO_3", "NO_4"]
OFFSHORE_ZONES = ["BE", "DK_1", "DK_2", "FR", "NL", "NO_2"]
PSR = {"solar": "B16", "wind_onsh": "B19", "wind_off": "B18", "hydro_res": "B12"}


def _actual(g: pd.DataFrame) -> pd.Series:
    """Keep the 'Actual Aggregated' generation column, whatever the layout."""
    if isinstance(g, pd.Series):
        return g
    if isinstance(g.columns, pd.MultiIndex):
        g = g.copy()
        g.columns = g.columns.get_level_values(-1)
    for c in g.columns:
        if str(c) == "Actual Aggregated":
            return g[c]
    return g.iloc[:, 0]


def main():
    from entsoe import EntsoePandasClient
    key = os.environ.get("ENTSOE_API_KEY")
    if not key:
        sys.exit("Set ENTSOE_API_KEY in the environment.")
    client = EntsoePandasClient(api_key=key)

    loads = []
    for z in LOAD_ZONES:
        print(f"load {z}")
        s = client.query_load(country_code=z, start=START, end=END)
        loads.append(_actual(s).rename(f"Load_{z}"))
    load = pd.concat(loads, axis=1)
    load.to_pickle(C.DATA_RAW / "load_neighbor_n_core_mid2022-2025.pkl")

    gens = []
    jobs = ([(z, "solar") for z in VRE_ZONES] + [(z, "wind_onsh") for z in VRE_ZONES]
            + [(z, "wind_off") for z in OFFSHORE_ZONES] + [("FR", "hydro_res")])
    for z, tech in jobs:
        try:
            g = client.query_generation(country_code=z, start=START, end=END,
                                        psr_type=PSR[tech])
            gens.append(_actual(g).rename(f"{tech}_{z}"))
            print(f"ok   {tech}_{z}")
        except Exception as e:                                  # noqa: BLE001
            print(f"fail {tech}_{z}: {e}")
    gen = pd.concat(gens, axis=1)
    gen.index.name = "DateTime"
    gen.to_pickle(C.DATA_RAW / "solar_windon_gen_neighbor.pkl")


if __name__ == "__main__":
    main()
