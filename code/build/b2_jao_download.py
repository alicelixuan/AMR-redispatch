"""
BUILD STEP 2 - Download JAO Core final-computation data (flow-based inputs)

    python code/build/b2_jao_download.py 2022 2023 2024 2025

For each day, requests the daily ZIP from the JAO Publication Tool API, keeps
German-internal (HubFrom and HubTo both DE), base-case (ContTso empty) CNEs in
DIRECT direction, and saves one parquet per published file to
data/raw/final_computation_<year>/. Already-downloaded days are skipped.

Source: notebook "5 - JAO_data.ipynb", cells 24-25.

NOTE: the original 2022 extract was assembled from a first download whose
request window ended at 23:00 (missing the last hour of each day) plus a
separate "last hour" download. This script uses the corrected window
(midnight to midnight), so no patch file is needed. 2022 is downloaded from
1 January; b3 trims to the sample start.
Requires network access to publicationtool.jao.eu.
"""
import calendar
import os
import sys
import time
import zipfile
from collections import Counter
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import requests  # noqa: E402
from requests.adapters import HTTPAdapter  # noqa: E402
from urllib3.util.retry import Retry  # noqa: E402

import config as C  # noqa: E402

BASE_URL = "https://publicationtool.jao.eu/core/api/data/finalComputation/download"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
           "Referer": "https://publicationtool.jao.eu/"}

session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])))


def download_and_extract(day, outdir):
    params = {"FromUtc": day.strftime("%Y-%m-%dT00:00:00.000Z"),
              "ToUtc": (day + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z"),
              "FileType": "csv", "Filter": ""}
    try:
        print(f"\nProcessing {day}...")
        r = session.get(BASE_URL, params=params, headers=HEADERS, timeout=(30, 300))
        r.raise_for_status()
        fr = session.get(r.json()["downloadUrl"], headers=HEADERS, timeout=(30, 900))
        fr.raise_for_status()
        z = zipfile.ZipFile(BytesIO(fr.content))
        for name in [f for f in z.namelist() if f.endswith(".csv")]:
            path = os.path.join(outdir, name.replace(".csv", ".parquet").replace("/", "_"))
            if os.path.exists(path):
                continue
            with z.open(name) as f:
                df = pd.read_csv(f, sep=";", low_memory=False)
            df["DateTime"] = pd.to_datetime(df["DateTimeUtc"], errors="coerce", utc=True)
            # German-internal, base-case CNECs only
            mask = (df["HubFrom"].astype(str).str.contains("DE", na=False)
                    & df["HubTo"].astype(str).str.contains("DE", na=False)
                    & df["ContTso"].isna())
            df = df.loc[mask]
            df["Direction"] = df["Direction"].astype(str)
            df = df.loc[df["Direction"] == "DIRECT"]
            df = df.drop_duplicates(subset=["CneEic", "Direction"], keep="first")
            df.to_parquet(path, index=False)
        return True
    except Exception as e:                                      # noqa: BLE001
        print(f"  error on {day}: {e}")
        return False
    finally:
        time.sleep(3)


def downloaded_counts(outdir):
    counts, prefix = Counter(), "finalComputation "
    for f in os.listdir(outdir):
        if f.startswith(prefix) and f.endswith(".parquet"):
            counts[f[len(prefix):len(prefix) + 10]] += 1
    return counts


def run_year(year):
    outdir = C.DATA_RAW / f"final_computation_{year}"
    outdir.mkdir(parents=True, exist_ok=True)
    counts = downloaded_counts(outdir)
    failed = []
    for m in range(1, 13):
        d = date(year, m, 1)
        while d <= date(year, m, calendar.monthrange(year, m)[1]):
            if counts[d.strftime("%Y-%m-%d")] < 24:
                if not download_and_extract(d, outdir):
                    failed.append(d)
            d += timedelta(days=1)
    print(f"{year}: {len(failed)} failed day(s): {failed}")


if __name__ == "__main__":
    for y in (sys.argv[1:] or ["2022", "2023", "2024", "2025"]):
        run_year(int(y))
