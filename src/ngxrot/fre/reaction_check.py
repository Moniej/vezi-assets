"""FRE-4: the deterministic cross-document reaction check
(docs/fre/06_cross_document_reasoning.md, Mechanism 2).

Reads realized price movement from the existing, validated PIT price panel
(`equity_prices`) and compares it against a fact's own qualitative
`direction` verdict -- a plain arithmetic comparison, never a new LLM call.
No schema change. No write path -- purely read-only, same zero-mutation
posture as company_memory.py.

## A real finding that changed this module's scope

Before writing anything, `investment_implications.market_reaction_
assessment`/`.market_reaction_reasoning` were inspected directly, since
Part 6's design assumed these columns were unpopulated. They are not: all
18 real implications already carry a value (17 'fairly_priced', 1
'unclear'), each with a DISTINCT, clearly LLM-generated reasoning string
("Standard annual dividend proposal... typically anticipated and priced
into equity markets," "Routine dividend announcement consistent with
standard yearly corporate calendar expectations," etc.) -- not a
hardcoded default. This is exactly the failure mode Part 6's design
warned about in the abstract ("an LLM asked 'did the market over/
underreact' would be reasoning about market efficiency from its own
priors... not evidence"), now CONFIRMED concretely: the existing AI
Intelligence Layer already answers this question, but by LLM speculation,
not by reading a single real price. The near-uniform "fairly_priced"
verdict (17/18) is itself a plausible mode-collapse pattern, similar in
shape to LIM's own RB-3b finding, though not independently proven here.

**Design consequence, stated explicitly**: this module does NOT overwrite
`market_reaction_assessment`/`market_reaction_reasoning` -- doing so would
modify AI Intelligence Layer data outside this program's scope, and would
erase the platform's own experiment history (the existing LLM verdict is
itself a real, disclosable data point, not garbage to replace). Instead,
`reaction_check()` computes an INDEPENDENT deterministic verdict and
returns it ALONGSIDE the existing value for comparison -- never
overwriting, only cross-checking.

## A second scope narrowing, also disclosed

Part 6's original sketch imagined this module directly producing
`market_reaction_assessment`'s own four-way vocabulary (`underreacting`/
`overreacting`/`fairly_priced`/`unclear`). Building it for real surfaces
why that is harder than it sounds: distinguishing "overreacting" from
"fairly priced" requires mapping a qualitative `magnitude` bucket
('tiny'/.../'transformational') to an expected NUMERIC return range --
exactly the kind of invented, unvalidated threshold
`docs/REASONING_ENGINE_SPECIFICATION.md` §6 explicitly refuses to create
("no numeric mapping is pre-defined... that would be inventing a
threshold with no evidence behind it"). This module therefore answers a
narrower, defensible question instead: does the SIGN of the realized
return agree with the fact's own `direction` verdict
('bullish'/'bearish'/'neutral'/'unknown')? This is `direction_confirmed`/
`direction_contradicted`/`inconclusive`/`not_applicable` -- a new,
explicitly separate vocabulary, never conflated with
`market_reaction_assessment`'s own enum.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# Heuristic, disclosed, NOT a validated threshold (same honesty this
# platform already applies to every other unvalidated constant): a realized
# return within this deadband is treated as "flat," not a real directional
# move, given typical NGX volatility. Picking a precise, evidence-backed
# value would require its own dedicated study -- not attempted here.
_FLAT_RETURN_DEADBAND = 0.01  # +/- 1%

# Heuristic liquidity floor, same disclosure: a `deals` count below this on
# EITHER anchor point flags the result as thin-liquidity, informational
# only -- it does not suppress the computed return, it accompanies it.
_THIN_LIQUIDITY_DEALS_FLOOR = 10


@dataclass
class ReactionCheckResult:
    implication_id: int
    ticker: str
    direction: str  # the fact's own qualitative verdict
    anchor_date: str  # documents.filing_date -- event_date is 0% populated today, disclosed substitution
    before_date: str | None
    before_close: float | None
    before_deals: int | None
    after_date: str | None
    after_close: float | None
    after_deals: int | None
    window_trading_rows: int  # how many trading rows were actually found after anchor_date
    realized_return: float | None  # None if price data is insufficient
    direction_check: str  # 'direction_confirmed' | 'direction_contradicted' | 'inconclusive' | 'not_applicable'
    thin_liquidity_flag: bool
    ex_dividend_confound_flag: bool  # True for fact_type='dividend' -- raw return is NOT reaction-only
    existing_market_reaction_assessment: str | None  # the AI layer's own, UNCHANGED, un-overwritten value
    existing_market_reaction_reasoning: str | None
    note: str


def reaction_check(con: sqlite3.Connection, implication_id: int, window_trading_days: int = 5) -> ReactionCheckResult:
    row = con.execute(
        """
        SELECT ii.ticker, ii.direction, ii.market_reaction_assessment, ii.market_reaction_reasoning,
               d.filing_date, f.fact_type
        FROM investment_implications ii
        JOIN extracted_facts f ON f.fact_id = ii.fact_id
        JOIN documents d ON d.doc_id = f.doc_id
        WHERE ii.implication_id = ?
        """,
        (implication_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no investment_implications row for implication_id={implication_id}")
    ticker, direction, existing_assessment, existing_reasoning, anchor_date, fact_type = row

    before_row = con.execute(
        "SELECT trade_date, close, deals FROM equity_prices WHERE ticker = ? AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1",
        (ticker, anchor_date),
    ).fetchone()
    after_rows = con.execute(
        "SELECT trade_date, close, deals FROM equity_prices WHERE ticker = ? AND trade_date > ? "
        "ORDER BY trade_date ASC LIMIT ?",
        (ticker, anchor_date, window_trading_days),
    ).fetchall()

    before_date, before_close, before_deals = before_row if before_row else (None, None, None)
    after_row = after_rows[-1] if after_rows else None
    after_date, after_close, after_deals = after_row if after_row else (None, None, None)

    realized_return: float | None = None
    if before_close and after_close:
        realized_return = (after_close - before_close) / before_close

    thin_liquidity = False
    if before_deals is not None and before_deals < _THIN_LIQUIDITY_DEALS_FLOOR:
        thin_liquidity = True
    if after_deals is not None and after_deals < _THIN_LIQUIDITY_DEALS_FLOOR:
        thin_liquidity = True

    ex_div_confound = fact_type == "dividend"

    if realized_return is None:
        direction_check = "inconclusive"
        note_bits = ["insufficient price data around the anchor date"]
    elif direction not in ("bullish", "bearish"):
        direction_check = "not_applicable"
        note_bits = [f"direction='{direction}' makes no directional claim to check"]
    elif abs(realized_return) < _FLAT_RETURN_DEADBAND:
        direction_check = "inconclusive"
        note_bits = [f"realized return {realized_return:.2%} is within the flat deadband "
                     f"(+/-{_FLAT_RETURN_DEADBAND:.0%}), too small to confirm or contradict a direction"]
    elif (direction == "bullish" and realized_return > 0) or (direction == "bearish" and realized_return < 0):
        direction_check = "direction_confirmed"
        note_bits = [f"realized return {realized_return:.2%} agrees with the stated '{direction}' direction"]
    else:
        direction_check = "direction_contradicted"
        note_bits = [f"realized return {realized_return:.2%} disagrees with the stated '{direction}' direction"]

    if thin_liquidity:
        note_bits.append(
            f"THIN LIQUIDITY (before_deals={before_deals}, after_deals={after_deals} vs. a "
            f"disclosed, unvalidated floor of {_THIN_LIQUIDITY_DEALS_FLOOR}) -- treat the "
            f"realized return with reduced confidence"
        )
    if ex_div_confound:
        note_bits.append(
            "EX-DIVIDEND CONFOUND -- this is a dividend fact; the raw close-to-close return "
            "is not adjusted for the mechanical ex-dividend price drop and should not be read "
            "as a pure market-sentiment reaction"
        )

    return ReactionCheckResult(
        implication_id=implication_id, ticker=ticker, direction=direction, anchor_date=anchor_date,
        before_date=before_date, before_close=before_close, before_deals=before_deals,
        after_date=after_date, after_close=after_close, after_deals=after_deals,
        window_trading_rows=len(after_rows), realized_return=realized_return,
        direction_check=direction_check, thin_liquidity_flag=thin_liquidity,
        ex_dividend_confound_flag=ex_div_confound,
        existing_market_reaction_assessment=existing_assessment,
        existing_market_reaction_reasoning=existing_reasoning,
        note="; ".join(note_bits),
    )
