"""
Run the whole replication in one go:

    python code/run_all.py

1. unzips the zipped data files in data/ (first run only)
2. build: b3 (JAO AMR by TSO) and b5 (hourly analysis panel)
3. analysis: every script in code/analysis/, in order

Tables go to output/tables/, figures to output/figures/. Script 01 must run
before the other analysis scripts: it stores the PDS-selected controls and
the main AMR coefficient that later scripts reuse. The run stops at the first
script that fails.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C  # noqa: E402
from lib.io import ensure_dirs, unzip_data  # noqa: E402

STEPS = [
    C.CODE / "build" / "b3_jao_amr.py",
    C.CODE / "build" / "b5_merge_panel.py",
    *sorted((C.CODE / "analysis").glob("[0-9][0-9]_*.py")),
]


def main():
    t_all = time.time()
    ensure_dirs()
    unzip_data()
    for s in STEPS:
        print(f"\n>>> {s.relative_to(C.ROOT)}", flush=True)
        t0 = time.time()
        if subprocess.run([sys.executable, str(s)], cwd=C.ROOT).returncode:
            sys.exit(f"\n{s.name} failed - stopping.")
        print(f"<<< {s.name} done in {time.time() - t0:,.0f}s", flush=True)
    print(f"\nAll done in {(time.time() - t_all) / 60:,.1f} min. "
          "Results are in output/tables and output/figures.")


if __name__ == "__main__":
    main()
