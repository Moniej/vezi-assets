"""LIM Economic Viability Audit — Phase 2: gold-standard extraction
benchmark. Every expected value below was read DIRECTLY from the real
document text at data/staging/document_text/<doc_id>.txt (production
documents, read-only) during this audit — not copied from a prior LLM
extraction, not assumed. Where a document is ambiguous in a real,
disclosed way, that ambiguity is noted in `notes` rather than resolved by
picking a convenient answer.

11 real documents, matching the exact stratified set used in the two prior
FRE pilots (2026-08-12), so this gold set is directly comparable to
Gemini's own already-measured performance on the same material — the
adversarial TRANSCORP 10x case (doc 9485) is included by explicit
instruction.
"""
from __future__ import annotations

GOLD_DOCUMENTS = [
    # --- True negatives: administrative/procedural notices, ZERO
    # quantitative financial facts. A correct extractor abstains
    # entirely; a dangerous one invents numbers that were never stated. ---
    {"doc_id": 8051, "ticker": "SEPLAT", "label": "true_negative",
     "expected_facts": [], "notes": "Pure webcast-scheduling notice. No figures at all."},
    {"doc_id": 8730, "ticker": "SEPLAT", "label": "true_negative",
     "expected_facts": [], "notes": "Same as 8051, different period. Zero figures."},
    {"doc_id": 3852, "ticker": "STANBIC", "label": "true_negative",
     "expected_facts": [], "notes": "Pure delay-notification. Zero figures."},
    {"doc_id": 8240, "ticker": "STANBIC", "label": "true_negative",
     "expected_facts": [], "notes": "Pure delay-notification. Zero figures."},
    {"doc_id": 8103, "ticker": "ELLAHLAKES", "label": "true_negative",
     "expected_facts": [], "notes": "CEO quote, operational milestones, no quantitative "
      "financial facts (mentions a rights-issue amount 'just over N250 million' but "
      "as prose color, not a statement line item — a correct extractor should not "
      "manufacture a structured fact_type=capital_raise from this)."},
    {"doc_id": 8158, "ticker": "MORISON", "label": "true_negative",
     "expected_facts": [], "notes": "Delay notice (2023 AFS). Zero figures."},
    {"doc_id": 9530, "ticker": "MORISON", "label": "true_negative",
     "expected_facts": [], "notes": "Delay notice (2024 AFS). Zero figures."},
    # --- Near-miss true negative: ONE qualitative claim, no number. The
    # adversarial risk here is a metric MISTAG (filing a qualitative
    # sentence under a quantitative fact_type), which is exactly what the
    # original Gemini pilot got wrong on this same document (fact_id=498,
    # tagged net_profit with numeric_value=NULL). ---
    {"doc_id": 452, "ticker": "STANBIC", "label": "qualitative_only",
     "expected_facts": [
         {"fact_type": None, "numeric_value": None, "notes":
          "'Stanbic IBTC Group remains well capitalised, liquid and continues to "
          "trade profitably' -- a qualitative claim with no number. Correct "
          "behavior: either don't extract it as a structured fact at all, or "
          "extract it as fact_type=qualitative_statement with numeric_value=null. "
          "INCORRECT: tagging it net_profit/any quantitative fact_type."},
     ], "notes": "This is the real document behind Gemini's own one confirmed "
      "metric-mistag (9/10 -> not 10/10 on fact-type accuracy)."},

    # --- Rich real quantitative documents (the actual target task) ---
    {"doc_id": 8750, "ticker": "TRANSCORP", "label": "quantitative",
     "period_start": "2024-01-01", "period_end": "2024-06-30", "period_type": "H1",
     "currency": "NGN", "expected_facts": [
        {"fact_type": "revenue", "numeric_value": 175_400_000_000},
        {"fact_type": "pbt", "numeric_value": 70_900_000_000},
        {"fact_type": "assets", "numeric_value": 625_100_000_000, "period_kind": "point_in_time"},
        {"fact_type": "equity", "numeric_value": 234_400_000_000, "period_kind": "point_in_time"},
        {"fact_type": "opex", "numeric_value": 21_200_000_000},
        {"fact_type": "dividend", "numeric_value": 0.10, "notes": "interim, 10 kobo/share = N0.10"},
     ], "notes": "Unaudited H1 2024 results. Comparative prior-period figures "
      "(N82.1bn revenue H1'23 etc.) are also stated in the SAME document -- a "
      "correct extractor must attribute each number to its OWN period, not "
      "conflate current and comparative periods under one period_end."},

    {"doc_id": 9485, "ticker": "TRANSCORP", "label": "quantitative_adversarial",
     "period_start": "2024-01-01", "period_end": "2024-12-31", "period_type": "FY",
     "currency": "NGN", "expected_facts": [
        {"fact_type": "revenue", "numeric_value": 408_000_000_000},
        {"fact_type": "pbt", "numeric_value": 136_700_000_000},
        {"fact_type": "net_profit", "numeric_value": 94_100_000_000,
         "notes": "**THE ADVERSARIAL CASE (per assignment).** Source text: 'Profit after "
          "Tax improved 188% year-on-year to N94.1 billion'. The real 2026-08-12 Gemini "
          "pilot stored this fact as 941,000,000,000 -- exactly 10x too large. A "
          "correct extractor must produce 94,100,000,000 here; 941,000,000,000 is the "
          "specific wrong answer this case exists to catch."},
        {"fact_type": "ebit", "numeric_value": 149_000_000_000, "notes":
         "Labelled 'Operating Income' in the source, N149.0bn -- the extractor must "
         "map 'Operating Income' to the platform's ebit fact_type, not skip it for "
         "not literally saying 'EBIT'."},
        {"fact_type": "opex", "numeric_value": 62_800_000_000},
        {"fact_type": "assets", "numeric_value": 751_600_000_000, "period_kind": "point_in_time"},
        {"fact_type": "equity", "numeric_value": 271_700_000_000, "period_kind": "point_in_time"},
        {"fact_type": "dividend", "numeric_value": 10_100_000_000, "notes":
         "Total N10.1bn OR N1.00/share -- both stated; either a valid extraction "
         "depending on which convention the schema wants, should not be confused "
         "with the 10.1 EPS figure below."},
     ], "notes": "FY2024 audited results. EPS (N1.45) and gearing ratio (21%) are "
      "also stated but are NOT in RATIO_DEFINITIONS' scope (EPS is a per-share "
      "figure requiring shares-outstanding context; gearing is itself a derived "
      "ratio, not a raw fact) -- not scored as required facts, but extracting them "
      "correctly if attempted is not penalized either."},

    {"doc_id": 11122, "ticker": "ELLAHLAKES", "label": "quantitative_adversarial",
     "period_start": "UNKNOWN_IRREGULAR", "period_end": "2025-12-31", "period_type": None,
     "currency": "NGN", "expected_facts": [
        {"fact_type": "revenue", "numeric_value": 146_658_000, "notes":
         "Confirmed twice: table line 'Revenue 146,658' (thousands) AND prose note "
         "'Revenue of N146,658,000 was recognised in the period'."},
        {"fact_type": "assets", "numeric_value": 28_257_351_000, "period_kind": "point_in_time",
         "notes": "GROUP consolidated column of a 4-column (Group/Company x "
          "current/prior) comparative table -- Company-only figure is "
          "11,494,107,000, a DIFFERENT real number in the same table. An extractor "
          "must pick one consistently and not silently average or conflate them."},
        {"fact_type": "liabilities", "numeric_value": 7_826_935_000, "period_kind": "point_in_time"},
        {"fact_type": "equity", "numeric_value": 20_430_416_000, "period_kind": "point_in_time",
         "notes": "Cross-confirmed in prose: \"total equity of N20,430,416,000\"."},
        {"fact_type": "net_profit", "numeric_value": -3_839_656_000, "notes":
         "GENUINE, DISCLOSED AMBIGUITY (not a scoring trap): the primary income "
         "statement states 'Profit/(Loss) after taxation (3,839,656)' (thousands, "
         "Group), but a note separately states 'Net loss for the 17-month period "
         "N3,856,655,000' -- a DIFFERENT figure, likely total comprehensive loss "
         "including OCI vs. profit-after-tax excluding it. -3,839,656,000 is scored "
         "as primary (matches the labelled income-statement line exactly); "
         "-3,856,655,000 is accepted as an alternate correct answer, not a wrong one."},
     ], "notes": "**SECOND ADVERSARIAL CASE.** The filing explicitly describes "
      "itself as covering a 'Net loss for the 17-month period' -- a genuinely "
      "IRREGULAR reporting period, not a clean FY, discovered by reading the "
      "source directly (this is the exact real-world case "
      "scripts/fre/test_period_extraction.py's own 'irregular 17-month period' "
      "test was built around). The correct behavior per this platform's own "
      "validate_period() is period_type=None (never force-mapped to FY), with "
      "the real dates preserved rather than discarded. All figures are in "
      "THOUSANDS of naira in the source table -- unit conversion to base units "
      "(x1000) is itself part of what's being tested."},

    {"doc_id": 9485, "ticker": "TRANSCORP", "label": "duplicate_reference_only",
     "expected_facts": [], "notes": "(listed once above under quantitative_adversarial; "
      "not a second entry -- kept as a single reference comment, not iterated twice "
      "by the scoring harness.)"},
]

# The scoring harness should drop the trailing 'duplicate_reference_only'
# placeholder entry before use -- it exists only as an in-file comment
# anchor, not real gold data.
GOLD_DOCUMENTS = [d for d in GOLD_DOCUMENTS if d["label"] != "duplicate_reference_only"]

TRUE_NEGATIVE_DOC_IDS = [d["doc_id"] for d in GOLD_DOCUMENTS if d["label"] == "true_negative"]
QUANTITATIVE_DOC_IDS = [d["doc_id"] for d in GOLD_DOCUMENTS if d["label"].startswith("quantitative")]
ADVERSARIAL_DOC_IDS = [d["doc_id"] for d in GOLD_DOCUMENTS if d["label"] == "quantitative_adversarial"]

if __name__ == "__main__":
    print(f"{len(GOLD_DOCUMENTS)} gold documents: "
         f"{len(TRUE_NEGATIVE_DOC_IDS)} true-negative, "
         f"1 qualitative-only, "
         f"{len(QUANTITATIVE_DOC_IDS)} quantitative "
         f"({len(ADVERSARIAL_DOC_IDS)} of which are adversarial cases)")
    total_expected_facts = sum(len(d["expected_facts"]) for d in GOLD_DOCUMENTS)
    print(f"total expected facts across gold set: {total_expected_facts}")
