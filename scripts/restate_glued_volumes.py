"""Restate equity_prices rows whose VOLUME glued to VALUE in the PRICES1 parse.

  python -u scripts/restate_glued_volumes.py            # dry-run: report only
  python -u scripts/restate_glued_volumes.py --apply    # write restatement rows

Failure mode (found 2026-07-21 via SEPLAT 2025-12-02): when a large volume
and a large naira value print with no gap in PRICES1.pdf, pdfplumber emits
ONE word ("3,459,46522,480,193,525.60"); the word-position parser assigns it
to the VOLUME column, so volume becomes a ~1e17..1e25 float and value_traded
NULL. Every corrupt row is source ngx_pricelist_v1 with volume > 1e12 and
value_traded NULL (no NGX stock trades 1e12 shares/day; verified no glued
row falls below that threshold — gluing needs both numbers wide).

Repair is archive-first: true values are re-derived from the archived
PRICES1.pdf text, never by splitting the stored float (REAL lost the digits).
The glued token is split at the unique point where BOTH halves are valid
comma-grouped numbers; rows whose TRADES also glued (deals NULL) get a
3-way split with the trades half required to match a small integer.
Cross-checks per row before anything is written:
  - trades half (2-way split) must equal the DB deals value;
  - float64 of the re-glued digits must equal the corrupt stored volume to
    1e-12 relative — what the parser's _num made of the token, except that
    ingest_pricelists' CSV->pd.to_numeric round-trip is lossy by ~1 ulp, so
    bitwise equality is unattainable; 1e-12 still rejects any different
    digit sequence (those disagree at >=1e-9 relative);
  - split must be unique; if several splits are comma-valid (same digits,
    different grouping) the one whose implied VWAP (value/volume) is within
    [0.25, 4]x close is taken, and only if exactly one qualifies.

Writes (append-only PIT): corrected row under the SAME source, as_of = today.
Corrupt rows captured TODAY (daily update ran before this fix) cannot get a
later same-granularity vintage — for those only, today's own capture row is
replaced in place (documented amendment of an intra-day state; no earlier
vintage is altered). Each restatement is logged to data_quality_log
(check_name='glued_volume_restated').
"""

import io
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db  # noqa: E402

ZIPS = ROOT / "data" / "archive" / "pricelist_zips"
NUM_RE = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")
VOL_THRESHOLD = 1e12


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def split_glued(tok: str, parts: int) -> list[tuple[str, ...]]:
    """All ways to split ``tok`` into ``parts`` valid comma-grouped numbers.
    Only the last part may carry decimals (VALUE); earlier parts (TRADES,
    VOLUME) must be integers."""
    if parts == 1:
        if NUM_RE.match(tok):
            return [(tok,)]
        return []
    out = []
    for i in range(1, len(tok)):
        head = tok[:i]
        if NUM_RE.match(head) and "." not in head:
            out.extend((head, *rest) for rest in split_glued(tok[i:], parts - 1))
    return out


def prices1_text(trade_date: str) -> str | None:
    hits = sorted(ZIPS.glob(f"{trade_date}_*.zip"))
    if not hits:
        return None
    z = zipfile.ZipFile(hits[0])
    member = next((n for n in z.namelist()
                   if re.fullmatch(r"PRICES[_ ]?1.*\.PDF", Path(n).name.upper())), None)
    if member is None:
        return None
    with pdfplumber.open(io.BytesIO(z.read(member))) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def _pick(cands: list[tuple[str, ...]], close: float, what: str
          ) -> tuple[tuple[str, ...] | None, str]:
    """Unique split, else VWAP-plausibility (value/volume within [0.25,4]x
    close) must single one out — comma grouping alone can be ambiguous
    because the digits are identical across candidate splits."""
    if len(cands) == 1:
        return cands[0], f"unique {what} of"
    ok = [c for c in cands
          if _num(c[-2]) > 0 and 0.25 <= (_num(c[-1]) / _num(c[-2])) / close <= 4]
    if len(ok) == 1:
        return ok[0], f"vwap-disambiguated {what} ({len(cands)} candidates) of"
    return None, f"AMBIGUOUS {what} ({len(cands)} candidates, {len(ok)} vwap-plausible):"


def recover_row(text: str, ticker: str, deals, close: float
                ) -> tuple[dict | None, str]:
    """Return (fix, note); fix = {volume, value, deals, glued} or None."""
    line = next((ln for ln in text.splitlines()
                 if re.match(rf"^\d+ {re.escape(ticker)} ", ln)), None)
    if line is None:
        return None, "row not found in PRICES1 text"
    toks = line.split()
    glued = toks[-1]
    if deals is not None:
        # TRADES printed separately: 2-way split of VOLUME+VALUE
        # cross-check: the token before the glue must be the known deals count
        if not re.fullmatch(r"[\d,]+", toks[-2]) or int(_num(toks[-2])) != int(deals):
            return None, f"trades token {toks[-2]!r} != deals {deals}"
        cand, note = _pick(split_glued(glued, 2), close, "2-way split")
        if cand is None:
            return None, f"{note} {glued!r}"
        vol_s, val_s = cand
        return {"volume": int(_num(vol_s)), "value": _num(val_s),
                "deals": int(deals), "glued": glued}, f"{note} {glued!r}"
    # deals NULL: TRADES+VOLUME+VALUE all glued — 3-way split, trades small
    cands = [c for c in split_glued(glued, 3) if _num(c[0]) < 100_000]
    cand, note = _pick(cands, close, "3-way split")
    if cand is None:
        return None, f"{note} {glued!r}"
    tr_s, vol_s, val_s = cand
    return {"volume": int(_num(vol_s)), "value": _num(val_s),
            "deals": int(_num(tr_s)), "glued": glued}, f"{note} {glued!r}"


def glue_float_match(fix: dict, corrupt_volume: float) -> bool:
    """float64 of the full glued token's digits must match the stored corrupt
    volume to 1e-12 relative (the parser's _num float, modulo the ~1-ulp-lossy
    CSV -> pd.to_numeric round-trip in ingest_pricelists)."""
    import math
    return math.isclose(float(fix["glued"].replace(",", "")), corrupt_volume,
                        rel_tol=1e-12)


def main() -> None:
    apply = "--apply" in sys.argv
    today = date.today().isoformat()
    con = db.connect()
    rows = con.execute(
        "SELECT ticker, trade_date, open, high, low, close, volume, deals, "
        "source_id, confidence, as_of_date FROM equity_prices "
        "WHERE volume > ? ORDER BY trade_date, ticker",
        (VOL_THRESHOLD,)).fetchall()
    print(f"corrupt rows (volume > {VOL_THRESHOLD:.0e}): {len(rows)}", flush=True)

    fixes, failures = [], []
    text_cache: dict[str, str | None] = {}
    for (tkr, td, o, h, l, c, vol, deals, src, conf, asof) in rows:
        if td not in text_cache:
            text_cache[td] = prices1_text(td)
        text = text_cache[td]
        if text is None:
            failures.append((tkr, td, "no PRICES1 pdf in archive"))
            continue
        fix, note = recover_row(text, tkr, deals, c)
        if fix is None:
            failures.append((tkr, td, note))
            continue
        if not glue_float_match(fix, vol):
            failures.append((tkr, td, f"glue-float cross-check failed: {fix} vs {vol!r}"))
            continue
        fixes.append(dict(ticker=tkr, trade_date=td, open=o, high=h, low=l,
                          close=c, source_id=src, confidence=conf,
                          old_asof=asof, old_volume=vol, note=note, **fix))

    print(f"\nrecovered: {len(fixes)} | failed: {len(failures)}\n", flush=True)
    for f in fixes:
        vwap = f["value"] / f["volume"] if f["volume"] else float("nan")
        print(f"  {f['trade_date']} {f['ticker']:<12} vol {f['old_volume']:.6e}"
              f" -> {f['volume']:>13,}  value {f['value']:>20,.2f}"
              f"  deals {f['deals']:>5}  vwap {vwap:,.2f} (close {f['close']:,})",
              flush=True)
    for tkr, td, why in failures:
        print(f"  FAIL {td} {tkr}: {why}", flush=True)

    if not apply:
        print("\ndry-run only — rerun with --apply to write restatements.", flush=True)
        return

    n_new = n_amended = 0
    for f in fixes:
        same_day = f["old_asof"] == today
        if same_day:
            # today's own capture: no later same-granularity vintage exists;
            # amend the intra-day row rather than fabricate a future as_of
            con.execute(
                "UPDATE equity_prices SET volume=?, value_traded=?, deals=? "
                "WHERE ticker=? AND trade_date=? AND source_id=? AND as_of_date=?",
                (f["volume"], f["value"], f["deals"],
                 f["ticker"], f["trade_date"], f["source_id"], today))
            n_amended += 1
        else:
            con.execute(
                "INSERT INTO equity_prices (ticker, trade_date, open, high, low, "
                "close, volume, value_traded, deals, source_id, confidence, "
                "as_of_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f["ticker"], f["trade_date"], f["open"], f["high"], f["low"],
                 f["close"], f["volume"], f["value"], f["deals"],
                 f["source_id"], f["confidence"], today))
            n_new += 1
        con.execute(
            "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
            "trade_date, severity, detail) VALUES (?,?,?,?,?,?)",
            ("glued_volume_restated", "ticker", f["ticker"], f["trade_date"],
             "info",
             f"restate_glued_volumes: corrupt volume {f['old_volume']!r} "
             f"(vintage {f['old_asof']}) -> volume={f['volume']} "
             f"value={f['value']} deals={f['deals']}; {f['note']}; "
             f"{'same-day amendment' if same_day else f'new vintage {today}'}"))
    con.commit()
    print(f"\napplied: {n_new} new as_of={today} vintage rows, "
          f"{n_amended} same-day amendments; {len(fixes)} logged to "
          f"data_quality_log.", flush=True)


if __name__ == "__main__":
    main()
