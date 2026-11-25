"""File helpers: format-agnostic reading, output directories, unzipping data."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

import config as C


def read_any(stem: Path | str) -> pd.DataFrame:
    """Read `stem` as .parquet, .pkl or .csv, whichever exists (in that order).

    Parquet is preferred for archiving (open, version-stable). Pickles written
    by one pandas major version may not load in another.
    """
    stem = Path(stem)
    candidates = [stem] if stem.suffix else [
        stem.with_suffix(s) for s in (".parquet", ".pkl", ".pickle", ".csv")]
    for p in candidates:
        if p.exists():
            if p.suffix == ".parquet":
                return pd.read_parquet(p)
            if p.suffix in (".pkl", ".pickle"):
                return pd.read_pickle(p)
            if p.suffix == ".csv":
                return pd.read_csv(p)
    raise FileNotFoundError(
        f"No input found for {stem} (tried {[c.name for c in candidates]}). "
        "See README section 'Data files'.")


def write_any(df: pd.DataFrame, stem: Path | str) -> Path:
    """Write parquet if pyarrow/fastparquet is available, else pickle."""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    try:
        p = stem.with_suffix(".parquet")
        df.to_parquet(p)
    except ImportError:
        p = stem.with_suffix(".pkl")
        df.to_pickle(p)
    print(f"[write] {p}  ({len(df):,} rows)")
    return p


def ensure_dirs():
    for d in (C.OUT_TABLES, C.OUT_FIGURES, C.OUT_INTERMEDIATE,
              C.DATA_INTERMEDIATE, C.DATA_ANALYSIS):
        d.mkdir(parents=True, exist_ok=True)


def unzip_data():
    """Extract every data/**/*.zip next to itself, once.

    Large inputs are stored zipped to stay under GitHub's 100 MB file limit,
    e.g. data/raw/foo.pkl.zip -> data/raw/foo.pkl. Files that already exist
    are left alone; macOS metadata (__MACOSX/, ._*) is skipped.
    """
    for z in sorted((C.ROOT / "data").rglob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for m in zf.infolist():
                name = Path(m.filename)
                if m.is_dir() or "__MACOSX" in name.parts or name.name.startswith("._"):
                    continue
                target = z.parent / name.name
                if not target.exists():
                    print(f"[unzip] {z.relative_to(C.ROOT)} -> {target.relative_to(C.ROOT)}")
                    tmp = target.with_name(target.name + ".part")
                    with zf.open(m) as src, tmp.open("wb") as dst:
                        while chunk := src.read(1 << 24):
                            dst.write(chunk)
                    tmp.replace(target)          # never leave a half-written file


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[write] {path.relative_to(C.ROOT)}")


def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")
    print(f"[write] {path.relative_to(C.ROOT)}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def banner(txt: str):
    print("\n" + "=" * 74 + f"\n{txt}\n" + "=" * 74, flush=True)


def setup_script():
    """Common start-up for every analysis script."""
    ensure_dirs()
    import matplotlib
    matplotlib.use("Agg")
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)
    print(f"python {sys.version.split()[0]} | pandas {pd.__version__}")
