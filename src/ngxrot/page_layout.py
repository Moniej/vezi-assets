"""Character-level page-layout analyzer for crowded NGX PDFs (IC directive).

Method:
  1. Row banding: glyphs clustered by baseline (top) tolerance.
  2. STREAM CHAINING: within a row, a text field's glyphs are mutually
     adjacent — each glyph starts where the previous one ends (x1 -> x0 gap
     within [-0.35, +1.2] pt). Overlapping COLUMNS interleave glyph x-order,
     but chaining by adjacency separates the original draw runs.
  3. Streams classified (date dd/mm/yy, number, text) and assigned to
     columns statistically: date-column x-bands are calibrated from CLEAN
     rows (rows whose date streams don't overlap), then every stream maps to
     the band containing its start-x.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DATE_RX = re.compile(r"^\d{2}/\d{2}/\d{2}$")
NUM_RX = re.compile(r"^-?[\d,]+(\.\d+)?$")


@dataclass
class Stream:
    text: str
    x0: float
    x1: float
    top: float


def rows_from_chars(chars: list[dict], tol: float = 2.5) -> list[list[dict]]:
    rows: dict[int, list] = {}
    for c in chars:
        rows.setdefault(round(c["top"] / tol), []).append(c)
    return [v for _, v in sorted(rows.items())]


def chain_streams(row_chars: list[dict], gap_lo: float = -0.35,
                  gap_hi: float = 1.2) -> list[Stream]:
    """Reconstruct draw-runs by x1->x0 adjacency chaining."""
    pool = sorted(row_chars, key=lambda c: c["x0"])
    used = [False] * len(pool)
    streams: list[Stream] = []
    for i, c in enumerate(pool):
        if used[i]:
            continue
        used[i] = True
        run = [c]
        cur = c
        while True:
            best, best_gap = None, None
            for j in range(len(pool)):
                if used[j]:
                    continue
                gap = pool[j]["x0"] - cur["x1"]
                if gap_lo <= gap <= gap_hi:
                    if best is None or gap < best_gap:
                        best, best_gap = j, gap
            if best is None:
                break
            used[best] = True
            cur = pool[best]
            run.append(cur)
        streams.append(Stream(text="".join(r["text"] for r in run).strip(),
                              x0=run[0]["x0"], x1=run[-1]["x1"],
                              top=run[0]["top"]))
    return [s for s in streams if s.text]


DATE_PATTERN = "dd/dd/dd"   # d = digit, / = slash


def extract_dates(row_chars: list[dict], gap_lo: float = -0.6,
                  gap_hi: float = 1.4) -> tuple[list[Stream], list[dict]]:
    """Format-aware extraction of dd/mm/yy dates from a (possibly
    column-overlapping) glyph row. At each chain step only glyphs matching
    the expected class (digit or '/') are candidates — this resolves
    interleaving collisions that defeat pure adjacency chaining. Returns
    (dates, leftover_chars)."""
    pool = sorted(row_chars, key=lambda c: c["x0"])
    used = [False] * len(pool)
    dates: list[Stream] = []

    def matches(ch: str, want: str) -> bool:
        return ch.isdigit() if want == "d" else ch == "/"

    for i, c in enumerate(pool):
        if used[i] or not c["text"].isdigit():
            continue
        run, run_idx, cur = [c], [i], c
        ok = True
        for want in DATE_PATTERN[1:]:
            best, best_key = None, None
            for j in range(len(pool)):
                if used[j] or j in run_idx:
                    continue
                gap = pool[j]["x0"] - cur["x1"]
                if gap_lo <= gap <= gap_hi and matches(pool[j]["text"], want):
                    key = abs(gap)
                    if best is None or key < best_key:
                        best, best_key = j, key
            if best is None:
                ok = False
                break
            run.append(pool[best])
            run_idx.append(best)
            cur = pool[best]
        if ok:
            text = "".join(r["text"] for r in run)
            dd, mm = int(text[:2]), int(text[3:5])
            if 1 <= dd <= 31 and 1 <= mm <= 12:
                for j in run_idx:
                    used[j] = True
                dates.append(Stream(text=text, x0=run[0]["x0"],
                                    x1=run[-1]["x1"], top=run[0]["top"]))
    leftovers = [pool[j] for j in range(len(pool)) if not used[j]]
    return dates, leftovers


def classify(s: Stream) -> str:
    if DATE_RX.match(s.text):
        return "date"
    if NUM_RX.match(s.text):
        return "number"
    return "text"
