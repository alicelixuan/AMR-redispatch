"""Paper-vs-replication comparison, appended to output/logs/replication_check.csv."""
from __future__ import annotations

import csv
import math

import config as C

_PATH = C.OUT_LOGS / "replication_check.csv"


def record(key: str, value: float, decimals: int | None = None):
    """Log a replicated number next to the published one.

    `decimals` is the precision printed in the paper; a match means the
    replicated value rounds to the published one at that precision.
    """
    paper = C.PAPER.get(key)
    if paper is None:
        status = "n/a"
    elif decimals is None:
        status = "MATCH" if math.isclose(value, paper, rel_tol=1e-3) else "DIFF"
    else:
        status = "MATCH" if round(value, decimals) == round(paper, decimals) else "DIFF"
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not _PATH.exists()
    with _PATH.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["result", "paper", "replicated", "status"])
        w.writerow([key, paper, f"{value:.6g}", status])
    flag = "" if status in ("MATCH", "n/a") else "   <-- check"
    print(f"  [check] {key:<26} paper={paper!s:<10} replicated={value:.6g}  {status}{flag}")


def reset():
    if _PATH.exists():
        _PATH.unlink()
