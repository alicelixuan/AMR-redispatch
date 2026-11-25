"""
BUILD STEP 1 - Netztransparenz redispatch orders -> 15-minute order rows

Input : data/raw/Redispatch_Daten.csv  (Netztransparenz export, ';'-separated,
        German number format, local CET/CEST start and end times)
Output: data/analysis/redispatch_orders_15min.{parquet|pkl}
        one row per (order, 15-minute interval it is active), all orders kept.
        Filtering to the outcome definition happens downstream
        (lib/descriptive.outcome_orders and code/build/b5_merge_panel.py).

Source: notebook "5 - redispatch_data.ipynb", cells 10-12 and 15.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from lib.io import write_any  # noqa: E402

RAW = C.DATA_RAW / "Redispatch_Daten.csv"


def main():
    netz = pd.read_csv(RAW, sep=";")

    # local start/end -> UTC
    tz_offset = {"CET": 1, "CEST": 2}
    for out, d, t, z in [("start", "BEGINN_DATUM", "BEGINN_UHRZEIT", "ZEITZONE_VON"),
                         ("end", "ENDE_DATUM", "ENDE_UHRZEIT", "ZEITZONE_BIS")]:
        netz[out] = (pd.to_datetime(netz[d] + " " + netz[t],
                                    format="%d.%m.%Y %H:%M", errors="coerce")
                     - pd.to_timedelta(netz[z].map(tz_offset), unit="h")
                     ).dt.tz_localize("UTC")
    netz = netz.drop(columns=["BEGINN_DATUM", "BEGINN_UHRZEIT", "ZEITZONE_VON",
                              "ENDE_DATUM", "ENDE_UHRZEIT", "ZEITZONE_BIS"])

    # German number format -> float
    netz["MITTLERE_LEISTUNG_MW"] = pd.to_numeric(
        netz["MITTLERE_LEISTUNG_MW"].astype(str)
        .str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce")

    # one row per active quarter-hour, [start, end)
    netz["intervals"] = netz.apply(
        lambda r: pd.date_range(start=r["start"], end=r["end"], freq="15min",
                                inclusive="left", tz="UTC"), axis=1)
    ts = netz.explode("intervals").rename(columns={"intervals": "DateTime"})
    ts = ts[["DateTime", "RICHTUNG", "MITTLERE_LEISTUNG_MW", "GRUND_DER_MASSNAHME",
             "ANWEISENDER_UENB", "ANFORDERNDER_UENB", "BETROFFENE_ANLAGE",
             "PRIMAERENERGIEART"]]
    ts.loc[ts["RICHTUNG"].str.contains("erh¿hen", case=False, na=False),
           "RICHTUNG"] = "Wirkleistungseinspeisung erhöhen"
    ts["MITTLERE_LEISTUNG_MWh"] = ts["MITTLERE_LEISTUNG_MW"] * 0.25
    ts["DateTime"] = pd.to_datetime(ts["DateTime"], utc=True)
    ts = ts.sort_values("DateTime").reset_index(drop=True)

    print(ts["GRUND_DER_MASSNAHME"].value_counts())
    write_any(ts, C.REDISPATCH_TS_FILE)


if __name__ == "__main__":
    main()
