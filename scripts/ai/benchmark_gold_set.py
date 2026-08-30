"""Gold-standard Nigerian financial-document benchmark set (2026-08-13, AI
Provider Expansion Phase 2). Every value below was read directly from the
real source document text at data/staging/document_text/{doc_id}.txt by a
human/agent reviewer (not derived from any model output), with an exact
source-line citation. This is the independently-verified ground truth the
benchmark grades against -- "the source document is the authority," not
model agreement.

Coverage, by design: bank (STANBIC-qualitative, UBA), insurance (AFRIPRUD),
consumer goods (CAP), conglomerate (TRANSCORP, UACN), energy (OANDO),
telecom (MTNN), agriculture/mandatory-regression (ELLAHLAKES), thin/
true-negative (MORISON). ₦, ₦'000, ₦ million, ₦ billion, ₦ trillion units
all represented. Two deliberate true-negative documents (STANBIC, MORISON
-- pure narrative, zero extractable numeric facts) to test hallucination
resistance, not just extraction recall.

Values are stored as the TRUE value in whole Naira (or USD where the
document itself is USD-denominated), matching the extraction schema's own
"numeric_value must always be the true value in whole units" contract --
grading compares a model's numeric_value directly against these, and
separately checks for 1e3x/1e6x scaling-error ratios.
"""
from __future__ import annotations

GOLD = {
    452: {  # STANBIC -- 2015 audited-statements delay notice, pure narrative
        "ticker": "STANBIC", "sector": "bank", "true_negative": True,
        "note": "Zero extractable numeric financial facts -- entirely a regulatory/"
               "legal narrative about a delayed filing. Correct model behavior is "
               "facts=[] or very close to it; ANY fabricated revenue/profit/asset "
               "figure here is a hallucination by construction.",
        "facts": [],
    },
    9530: {  # MORISON -- delay-in-filing notice, pure narrative
        "ticker": "MORISON", "sector": "industrial", "true_negative": True,
        "note": "Zero extractable numeric financial facts -- delay-in-filing notice "
               "only. Same hallucination-resistance test as STANBIC.",
        "facts": [],
    },
    9485: {  # TRANSCORP -- FY2024 results press release, prose-only, N-billion scale words
        "ticker": "TRANSCORP", "sector": "conglomerate", "true_negative": False,
        "note": "Prose-only (no table). Scale words stated inline (N billion). This "
               "is the ORIGINAL real TRANSCORP 10x prose-scale case from Gate 2 -- "
               "PAT=N94.1bn is the exact figure that case is built around.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2024-12-31", "period_type": "FY",
             "value": 408_000_000_000, "tolerance_pct": 0.01, "source_line": 11},
            {"fact_type": "revenue", "period_end": "2023-12-31", "period_type": "FY",
             "value": 197_000_000_000, "tolerance_pct": 0.01, "source_line": 14,
             "note": "prior-year comparative, same fact_type"},
            {"fact_type": "net_profit", "period_end": "2024-12-31", "period_type": "FY",
             "value": 94_100_000_000, "tolerance_pct": 0.01, "source_line": 18,
             "note": "labeled 'Profit after Tax' -- maps to net_profit taxonomy leaf"},
            {"fact_type": "assets", "period_end": "2024-12-31", "period_type": "FY",
             "value": 751_600_000_000, "tolerance_pct": 0.01, "source_line": 37},
            {"fact_type": "assets", "period_end": "2023-12-31", "period_type": "FY",
             "value": 529_900_000_000, "tolerance_pct": 0.01, "source_line": 36},
        ],
    },
    4245: {  # AFRIPRUD -- Q3 2020 unaudited results, thousands-table + reversed column order
        "ticker": "AFRIPRUD", "sector": "insurance", "true_negative": False,
        "note": "Table header 'In thousands of Nigerian Naira' (line 85/131) -- true "
               "unit test. IMPORTANT real source-document defect: the TOTAL "
               "LIABILITIES (line 158-159) and TOTAL EQUITY (line 171-172) table rows "
               "print their two period columns in REVERSED order relative to the "
               "table's own header row -- confirmed by cross-checking against the "
               "prose paragraph (lines 46-49), which is unambiguous. Gold values "
               "below are the prose-confirmed CORRECT figures, not the naive "
               "first-column table read. period_type: the document labels this period "
               "'Q3 2020' throughout (lines 1, 37-49) even though it is calendar-YTD "
               "(Jan-Sep) in substance -- same genuine self-label-vs-substance "
               "ambiguity as the UBA case below; both 'Q3' (document's own label) and "
               "'9M' (substance) are accepted.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2020-09-30", "period_type": ("Q3", "9M"),
             "value": 860_787_000, "tolerance_pct": 0.01, "source_line": 87,
             "note": "'Revenue from Contracts with customers', thousands-table"},
            {"fact_type": "net_profit", "period_end": "2020-09-30", "period_type": ("Q3", "9M"),
             "value": 1_410_129_000, "tolerance_pct": 0.01, "source_line": 113},
            {"fact_type": "assets", "period_end": "2020-09-30", "period_type": None,
             "value": 19_378_978_000, "tolerance_pct": 0.01, "source_line": 146},
            {"fact_type": "liabilities", "period_end": "2020-09-30", "period_type": None,
             "value": 11_109_828_000, "tolerance_pct": 0.02, "source_line": 159,
             "note": "REVERSED-COLUMN CASE -- correct value confirmed via prose line 47 "
                    "('N11.11 Billion'), not the naive first printed column (10,365,049)"},
            {"fact_type": "equity", "period_end": "2020-09-30", "period_type": None,
             "value": 8_269_150_000, "tolerance_pct": 0.02, "source_line": 172,
             "note": "REVERSED-COLUMN CASE -- correct value confirmed via prose line 48 "
                    "('N8.27 Billion'), not the naive first printed column (8,284,284)"},
        ],
    },
    4508: {  # CAP -- Q4/FY2020 results, million-Naira table, prose/table EPS discrepancy
        "ticker": "CAP", "sector": "consumer_goods", "true_negative": False,
        "note": "Table header 'In million N, unless otherwise stated' (line 54). Real "
               "source-document ambiguity: prose (line 47) states EPS='182 kobo' but "
               "the table (line 73) states FY2020 EPS=184 kobo -- an inconsistency IN "
               "THE SOURCE DOCUMENT ITSELF, not a benchmark artifact. Gold value uses "
               "the table (the platform's own established discipline: structured "
               "table > prose synopsis on conflict) -- a model citing 182 with correct "
               "attribution to the prose is not penalized as harshly as one inventing "
               "a third value. Also: 'Cash and cash equivalents' row (line 79) prints "
               "under a REVERSED header ('Dec-19 Dec-20' order but data is Dec-20-first) "
               "-- confirmed via prose line 51 ('N5.8 billion' current cash position).",
        "facts": [
            {"fact_type": "revenue", "period_end": "2020-12-31", "period_type": "FY",
             "value": 8_737_000_000, "tolerance_pct": 0.01, "source_line": 55},
            {"fact_type": "revenue", "period_end": "2019-12-31", "period_type": "FY",
             "value": 8_411_000_000, "tolerance_pct": 0.01, "source_line": 55},
            {"fact_type": "ebit", "period_end": "2020-12-31", "period_type": "FY",
             "value": 1_645_000_000, "tolerance_pct": 0.01, "source_line": 63},
            {"fact_type": "net_profit", "period_end": "2020-12-31", "period_type": "FY",
             "value": 1_289_000_000, "tolerance_pct": 0.01, "source_line": 72,
             "note": "'Profit After Tax' row"},
            {"fact_type": "gross_profit", "period_end": "2020-12-31", "period_type": "FY",
             "value": 3_755_000_000, "tolerance_pct": 0.01, "source_line": 56},
        ],
    },
    5163: {  # UACN -- H1 2021 results, million-Naira table, discontinued operations
        "ticker": "UACN", "sector": "conglomerate", "true_negative": False,
        "note": "Table header 'In million N, unless otherwise stated' (line 28). "
               "Continuing-vs-discontinued-operations distinction is explicit and "
               "important: H1 2020 net_profit includes a large one-off N944m "
               "discontinued-operations profit (line 44) that does NOT recur in H1 "
               "2021 -- a model that reports H1 2020 net_profit=1,158m (total) without "
               "distinguishing continuing (214m) vs total is not WRONG but loses "
               "points on semantic/evidence precision if it doesn't note the split, "
               "since the prose headline explicitly calls out continuing operations.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2021-06-30", "period_type": "H1",
             "value": 46_499_000_000, "tolerance_pct": 0.01, "source_line": 29},
            {"fact_type": "revenue", "period_end": "2020-06-30", "period_type": "H1",
             "value": 36_633_000_000, "tolerance_pct": 0.01, "source_line": 29},
            {"fact_type": "ebit", "period_end": "2021-06-30", "period_type": "H1",
             "value": 1_700_000_000, "tolerance_pct": 0.01, "source_line": 37},
            {"fact_type": "net_profit", "period_end": "2021-06-30", "period_type": "H1",
             "value": 763_000_000, "tolerance_pct": 0.02, "source_line": 45,
             "note": "total 'Profit for the period', continuing (765m) + discontinued (-2m)"},
            {"fact_type": "gross_profit", "period_end": "2021-06-30", "period_type": "H1",
             "value": 8_324_000_000, "tolerance_pct": 0.01, "source_line": 30},
        ],
    },
    10625: {  # OANDO -- FY2025 results, prose-only, N-trillion scale
        "ticker": "OANDO", "sector": "energy", "true_negative": False,
        "note": "Prose-only (no table in this press release). N-TRILLION scale word "
               "(distinct from the billion/million cases elsewhere in this set) -- "
               "line 48. PAT increased 10% YoY despite gross profit collapsing 82% "
               "YoY -- a real, correct, non-obvious pattern (driven by impairment "
               "reversals per line 55); a model 'smoothing' this into a generic "
               "positive/negative narrative without preserving the actual divergent "
               "signs would be a reasoning-quality failure, not a numeric one.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2025-12-31", "period_type": "FY",
             "value": 3_210_000_000_000, "tolerance_pct": 0.01, "source_line": 48},
            {"fact_type": "revenue", "period_end": "2024-12-31", "period_type": "FY",
             "value": 4_090_000_000_000, "tolerance_pct": 0.01, "source_line": 48},
            {"fact_type": "gross_profit", "period_end": "2025-12-31", "period_type": "FY",
             "value": 27_800_000_000, "tolerance_pct": 0.01, "source_line": 51},
            {"fact_type": "net_profit", "period_end": "2025-12-31", "period_type": "FY",
             "value": 241_300_000_000, "tolerance_pct": 0.01, "source_line": 54},
            {"fact_type": "capex", "period_end": "2025-12-31", "period_type": "FY",
             "value": 101_900_000_000, "tolerance_pct": 0.01, "source_line": 57},
        ],
    },
    7793: {  # UBA -- Q3 2023 results, million-Naira table, period-comparability nuance
        "ticker": "UBA", "sector": "bank", "true_negative": False,
        "note": "Table header '₦ Million' (lines 6/18). REAL period-type ambiguity: "
               "labeled 'Q3'2023' but the absolute scale (N1.3 trillion gross earnings) "
               "is far too large for a single quarter at this bank's run-rate -- this "
               "is very likely 9M-cumulative-to-date mislabeled 'Q3' (a known NGX "
               "quarterly-filing convention). Grading treats period_type='Q3' OR '9M' "
               "as acceptable given the source document's own genuine ambiguity; "
               "period_end=2023-09-30 must still be correct regardless. Separately: "
               "balance-sheet comparative is 'YE'2022' (prior FY-end) while income- "
               "statement comparative is 'Q3'2022' (prior-year same quarter) -- "
               "correct statement-type-specific comparatives, a real accounting nuance.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2023-09-30", "period_type": ("Q3", "9M"),
             "value": 1_308_861_000_000, "tolerance_pct": 0.01, "source_line": 7,
             "note": "'Gross earnings' row"},
            {"fact_type": "net_profit", "period_end": "2023-09-30", "period_type": ("Q3", "9M"),
             "value": 449_296_000_000, "tolerance_pct": 0.01, "source_line": 14,
             "note": "'Profit after tax' row"},
            {"fact_type": "assets", "period_end": "2023-09-30", "period_type": None,
             "value": 16_235_995_000_000, "tolerance_pct": 0.01, "source_line": 19},
            {"fact_type": "assets", "period_end": "2022-12-31", "period_type": None,
             "value": 10_857_571_000_000, "tolerance_pct": 0.01, "source_line": 19,
             "note": "comparative is YE'2022 (prior FY-end), NOT Q3'2022"},
            {"fact_type": "equity", "period_end": "2023-09-30", "period_type": None,
             "value": 1_778_132_000_000, "tolerance_pct": 0.01, "source_line": 22,
             "note": "'Shareholders' funds' row"},
        ],
    },
    6393: {  # MTNN -- H1 2022 results, prose-only, N-billion scale, ambiguous EPS label
        "ticker": "MTNN", "sector": "telecom", "true_negative": False,
        "note": "Prose-only (no table in this excerpt). Real source-document labeling "
               "ambiguity: EPS is stated as 'N8.92 kobo' (line 32) and dividend as "
               "'N5.60 kobo' (line 38) -- mixing a Naira symbol with a kobo unit label "
               "in the SAME phrase, an inconsistency in the source text itself. Gold "
               "value below is the numeric magnitude (8.92) with unit left ambiguous "
               "on purpose -- grading checks numeric_value=8.92 was captured and "
               "notes (does not penalize) how each model resolved the naira-vs-kobo "
               "ambiguity, since the document itself is not resolvable with certainty.",
        "facts": [
            {"fact_type": "revenue", "period_end": "2022-06-30", "period_type": "H1",
             "value": 947_900_000_000, "tolerance_pct": 0.01, "source_line": 22,
             "note": "'Service revenue'"},
            {"fact_type": "ebitda", "period_end": "2022-06-30", "period_type": "H1",
             "value": 509_300_000_000, "tolerance_pct": 0.01, "source_line": 25},
            {"fact_type": "net_profit", "period_end": "2022-06-30", "period_type": "H1",
             "value": 181_600_000_000, "tolerance_pct": 0.01, "source_line": 30,
             "note": "'Profit after tax (PAT)'"},
            {"fact_type": "capex", "period_end": "2022-06-30", "period_type": "H1",
             "value": 311_600_000_000, "tolerance_pct": 0.01, "source_line": 34},
        ],
    },
    11122: {  # ELLAHLAKES -- MANDATORY regression case, real 1000x defect origin
        "ticker": "ELLAHLAKES", "sector": "agriculture", "true_negative": False,
        "mandatory": True,
        "note": "MANDATORY regression benchmark (docs/alpha/AUTONOMOUS_FRE_PROGRESS_"
               "2026-08-13.md, Entry 1) -- the real document whose table-header ₦'000 "
               "convention caused a live, systematic ~1000x scaling error before the "
               "v3 prompt fix (DRAFT_PROMPT_VERSION bump) was built. Every model in "
               "this benchmark uses the SAME v3 prompt (build_draft_prompt, unchanged) "
               "-- this case specifically tests whether each model (not just Gemini) "
               "correctly applies a table-header ₦'000 scale declaration, independent "
               "of the deterministic numeric_consistency safety net that would "
               "otherwise catch (not fix) an unscaled figure downstream. 17-month "
               "irregular period (2024-08-01 to 2025-12-31) -- period_type must be "
               "null, not force-mapped to FY (see prior investigation, trend-duration "
               "guard already handles the downstream comparability gap separately).",
        "facts": [
            {"fact_type": "revenue", "period_end": "2025-12-31", "period_type": None,
             "value": 146_658_000, "tolerance_pct": 0.01, "source_line": "confirmed via "
             "data/staging/document_text/11122.txt lines 67-76 (Gate-2 finding)",
             "note": "CATASTROPHIC-ERROR CHECK: unscaled table figure was 146,658 -- a "
                    "model returning ~146658 instead of ~146658000 has the exact "
                    "1000x scaling defect this case exists to catch."},
            {"fact_type": "net_profit", "period_end": "2025-12-31", "period_type": None,
             "value": -3_839_656_000, "tolerance_pct": 0.01,
             "note": "unscaled table figure was -3,839,656 -- same 1000x check, negative sign"},
            {"fact_type": "assets", "period_end": "2025-12-31", "period_type": None,
             "value": 28_257_351_000, "tolerance_pct": 0.01,
             "note": "unscaled table figure was 28,257,351 -- same 1000x check"},
            {"fact_type": "liabilities", "period_end": "2025-12-31", "period_type": None,
             "value": 7_826_935_000, "tolerance_pct": 0.01,
             "note": "unscaled table figure was 7,826,935 -- same 1000x check"},
        ],
    },
}

# fact_type set actually requested by the shared v3 prompt (PILOT_FACT_TYPES)
# -- used to sanity-check that every gold fact_type is one the model was
# actually asked to look for.
from ngxrot.documents.prompts import PILOT_FACT_TYPES  # noqa: E402
for doc_id, spec in GOLD.items():
    for f in spec["facts"]:
        assert f["fact_type"] in PILOT_FACT_TYPES, \
            f"gold fact_type {f['fact_type']!r} (doc {doc_id}) not in PILOT_FACT_TYPES"
