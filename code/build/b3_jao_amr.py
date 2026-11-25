"""
BUILD STEP 3 - JAO final computation -> CNE-level minRAM file -> TSO-level AMR

Input : data/raw/final_computation_<year>/*.parquet  (from b2), years 2022-2025
Output: data/intermediate/minRAM.{parquet|pkl}   CNE x hour (all columns)
        data/analysis/amr_tso.{parquet|pkl}       base-case AMR summed over
                                                  CNEs, by (DateTime, TSO)

Sources: "5 - JAO_data.ipynb" cells 27-29, 40-42, 45;
         "5 - Trade_on_redispatch.ipynb" cells 26 and 28.
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from lib.io import read_any, write_any  # noqa: E402

YEARS = [2022, 2023, 2024, 2025]
TSO_NAMES = {"50HERTZ": "50Hertz", "AMPRION": "Amprion",
             "TENNETGMBH": "TenneT DE", "TRANSNETBW": "TransnetBW"}


def compile_year(year):
    frames = []
    for f in sorted(glob.glob(str(C.DATA_RAW / f"final_computation_{year}" / "*.parquet"))):
        df = pd.read_parquet(f)
        df["Direction"] = df["Direction"].astype(str)
        df = df.loc[df["Direction"] == "DIRECT"]
        frames.append(df.drop_duplicates(subset=["CneEic", "Direction"], keep="first"))
    if not frames:
        raise FileNotFoundError(f"no parquet files for {year}; run b2 first")
    df = pd.concat(frames, ignore_index=True).dropna(axis=1, how="all")
    df = df.drop(columns=[c for c in ("Id", "DateTimeUtc", "Direction") if c in df])
    return df.sort_values("DateTime")


def main():
    try:
        # Default: the shipped data/intermediate/minRAM.parquet (the columns
        # DateTime, Tso, CneEic, Amr, MinRamFactor of the full JAO extract).
        mr = read_any(C.DATA_INTERMEDIATE / "minRAM")
        print("[b3] using existing data/intermediate/minRAM")
    except FileNotFoundError:
        mr = pd.concat([compile_year(y) for y in YEARS])
        mr["RamFactor"] = mr["Ram"] / mr["Fmax"] * 100
        keep = {"DateTime", "Tso", "CneEic", "Amr", "MinRamFactor"}
        mr = mr.loc[:, (mr.nunique(dropna=False) > 1) | mr.columns.isin(keep)]
        mr = mr.loc[mr["DateTime"] >= pd.Timestamp("2022-06-08", tz="UTC")]
        write_any(mr.reset_index(drop=True), C.DATA_INTERMEDIATE / "minRAM")
    mr["DateTime"] = pd.to_datetime(mr["DateTime"], utc=True)

    # --- TSO-level AMR (Trade_on_redispatch cells 26, 28) ---
    jao = mr.drop_duplicates(subset=["DateTime", "CneEic"], keep="first")
    # 126 rows with MinRamFactor 505 at 2024-03-27 23:00 UTC are a publication error
    jao = jao.loc[jao["MinRamFactor"] < 500]
    jao = jao.loc[jao["DateTime"] > pd.Timestamp("2022-06-01", tz="UTC")]
    jao = jao.rename(columns={"Tso": "TSO"})
    amr = jao.groupby(["DateTime", "TSO"])[["Amr"]].sum()
    amr = amr.rename(index=TSO_NAMES, level="TSO")
    write_any(amr, C.AMR_TSO_FILE)


if __name__ == "__main__":
    main()
