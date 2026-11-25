"""
Run every analysis script in order and write a paper-vs-replication check.

    python code/run_all.py            # everything (Section 6 + appendix)
    python code/run_all.py 01 07      # only scripts whose name starts with 01 or 07

Each script's console output is also saved to output/logs/<script>.log.
Script 01 must run before the others: it stores the PDS-selected controls
and the main AMR coefficient that later scripts reuse.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C  # noqa: E402
from lib import check  # noqa: E402
from lib.io import ensure_dirs  # noqa: E402

SCRIPTS = sorted((C.CODE / "analysis").glob("[0-9][0-9]_*.py"))


def main(argv):
    ensure_dirs()
    chosen = [s for s in SCRIPTS if not argv or any(s.name.startswith(a) for a in argv)]
    if not argv:
        check.reset()
    failed = []
    t_all = time.time()
    for s in chosen:
        log = C.OUT_LOGS / f"{s.stem}.log"
        print(f"\n>>> {s.name}  (log: {log.relative_to(C.ROOT)})", flush=True)
        t0 = time.time()
        with log.open("w", encoding="utf-8") as fh:
            p = subprocess.Popen([sys.executable, str(s)], cwd=C.ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True)
            for line in p.stdout:
                sys.stdout.write(line)
                fh.write(line)
            p.wait()
        status = "ok" if p.returncode == 0 else f"FAILED (exit {p.returncode})"
        print(f"<<< {s.name}: {status} in {time.time() - t0:,.0f}s", flush=True)
        if p.returncode:
            failed.append(s.name)

    print(f"\nTotal runtime: {(time.time() - t_all) / 60:,.1f} min")
    chk = C.OUT_LOGS / "replication_check.csv"
    if chk.exists():
        import pandas as pd
        tab = pd.read_csv(chk)
        print("\nPaper vs replication:")
        print(tab.to_string(index=False))
        n_diff = int((tab["status"] == "DIFF").sum())
        print(f"\n{(tab['status'] == 'MATCH').sum()} match, {n_diff} differ "
              f"(at the precision printed in the paper)")
    if failed:
        print(f"\nFailed scripts: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
