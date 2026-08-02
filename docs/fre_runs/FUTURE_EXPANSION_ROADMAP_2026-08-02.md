# Future Expansion Roadmap — v1.0 (2026-08-02 Stable Baseline)

*Ordered strictly by dependency chain — what must happen before what
becomes possible — not by estimated value, priority, or ease. Each
node names its own trigger condition; nothing here should be started
until its own named trigger has actually occurred (see
`OWNER_DECISION_BACKLOG_2026-08-02.md` for exactly what each trigger
requires and how to verify it). This is a map of sequencing
constraints, not a recommendation of what to do first.*

## Chain A — Data-acquisition-rooted

```
[Owner allocates hand-extraction labor to more of the 39 remaining scoped tickers]
        │
        ▼
[Coverage expansion executes — same Phase 1/2/13 methodology, no new design]
        │
        ├──▶ [More real cfo/cfi/cff/fcf periods may accumulate as a side effect]
        │            │
        │            ▼
        │    [cfo/cfi/cff/fcf-based health flag becomes buildable]
        │
        ├──▶ [Screening/Watchlist/Sector-Coverage View's real coverage grows]
        │    (zero code change needed — every Part 9 module already
        │     operates on list_tickers()'s live, dynamic roster)
        │
        └──▶ [More tickers may acquire a known sector_ngx if new filings
              happen to be covered by NGX's Daily Official List]
```

```
[A different/historical NGX sector document is sourced, OR owner
 confirms delisting status for the 184 currently-unmatched securities]
        │
        ▼
[securities.sector_ngx coverage grows beyond 136/320]
        │
        ├──▶ [Sector-Coverage View's UNKNOWN bucket shrinks — zero code
        │     change, sector_coverage.py already handles any coverage level]
        │
        └──▶ [Sector-to-Company-Type Mapping resolves more tickers —
              zero code change, sector_company_type_mapping.py already
              handles any coverage level]
```

```
[A new extraction pass identifies real subsidiary_of lineage edges]
        │
        ▼
[sum_of_the_parts valuation adapter becomes buildable for real
 holding-company-classified tickers (CONGLOMERATES sector, Phase 26)]
        │
        ▼
[Still gated behind: a future, separate, explicit architecture-
 revision authorization to activate ANY valuation compute() output —
 this chain does not bypass that gate, it only removes the DATA
 blocker; the GUARDRAIL blocker (Chain D) is independent]
```

```
[A new extraction pass identifies real macro_exposure edges
 (exposed_to_commodity/exposed_to_fx/exposed_to_policy)]
        │
        ▼
[correlation_notes.py starts returning real, non-empty notes —
 zero code change needed, already correctly architected]
        │
        ▼
[A CLI wrapper for correlation_notes.py becomes worth building
 (currently not-currently-justified: no real output to show)]
```

## Chain B — Vendor/provider-rooted

```
[Owner selects an OCR engine/vendor]
        │
        ▼
[36% of the document archive (4,134 documents) becomes text-accessible]
        │
        ├──▶ [Potential new extraction candidates for coverage expansion
        │     (Chain A), pending owner's own labor-allocation decision]
        │
        └──▶ [GTCO/Zenith's own originally-named pilot anchors
              (currently unreachable, scanned PDFs) become reachable]
```

```
[Owner selects exact Qwen3.x checkpoint/version]
        │
        ▼
[LIM Phase LIM-0 becomes startable — LIM-1 through LIM-8 follow in
 their own already-designed sequence, docs/LIM_ARCHITECTURE.md]
        │
        ▼
[Eventually, LIM could replace the current hosted-provider (Gemini)
 reasoning generation step — a large, separately-scoped future
 initiative, not a quick follow-on to the checkpoint decision alone]
```

```
[Owner resolves the Analyst Research licensing question]
        │
        ▼
[AnalystResearchProvider becomes buildable — Part 6's Analyst Notes
 source type activates]
```

## Chain C — Human-judgment-rooted

```
[An analyst authors a gold-standard label set]
        │
        ▼
[Evaluation Framework (FRE-10 / Part 11) becomes buildable —
 fully designed already, docs/fre/11_evaluation_framework.md]
        │
        ▼
[Every other FRE/FSI capability gains a real, measured quality score
 for the first time — currently every phase's own regression harness
 checks correctness/reproducibility, not the eleven owner-named
 quality dimensions Part 11 itself defines]
```

```
[Owner/analyst vets a Nigerian financial news outlet reliability list]
        │
        ▼
[evidence_ranking.py's news-source TrustAssignment stops being
 provisional]
        │
        ▼
[News corpus harvesting (NewsDocumentProvider, not yet built) becomes
 worth prioritizing — currently blocked on this decision AND its own
 separate harvest-infrastructure build]
```

```
[Owner rules on the 3 unresolved Financial-Services sub-industries
 (Micro-Finance Banks, Mortgage Carriers, "Other Financial
 Institutions") in sector_company_type_mapping.toml]
        │
        ▼
[The 12 real tickers currently falling back to "general" under these
 sub-industries get a more precise company_type classification —
 config-only change, zero code change]
```

## Chain D — Guardrail-revision-rooted (the platform's own hardest gate)

```
[A second validated quant factor confirms (Wave-3/H-0xx research track,
 pre-registration + gauntlet + placebo/power tests — the Quant
 Engine's own unchanged process, never shortcut by FRE/FSI)]
        │
        ▼
[Portfolio Construction's own ≥2-factor gate opens]
        │
        ▼
[Part 9 Tier 2 (ranking, position sizing, conviction-weighted
 allocation) becomes DESIGN-READY — Part 9's own document already
 names the interfaces each Tier-2 capability will need
 (CompanyThesis.confidence, validated_factor_exposure), but building
 Tier 2 itself is its own separately-scoped, separately-authorized
 initiative, not something this chain auto-unlocks]
        │
        ▼
[Revisit Part 8 (Valuation Engine activation) and Part 9 Tier 2
 TOGETHER, per this program's own long-tanding recommendation —
 they were designed together and share the same precondition]
```

```
[A future, separate, explicit architecture-revision authorization
 (independent of any data or factor-validation event) permits
 activating a valuation compute() output]
        │
        ▼
[One of the six existing ValuationMethodAdapter subclasses'
 compute() methods gets a real formula, for the FIRST company/method
 pair where is_ready()=True AND a formula has been validated]
        │
        ▼
[TriangulatedValuation.results stops being permanently empty for
 that pair — this is the single most consequential unlock on this
 entire roadmap, and the one this program has been most careful
 never to reach accidentally]
```

## How to use this roadmap

Nothing above should be started speculatively. Each chain's own root
trigger is the ONLY valid reason to begin; starting partway down a
chain without its own root trigger having actually occurred would
reintroduce exactly the kind of premature/unjustified phase this
program's own standing discipline was built to prevent. When a
trigger does occur, re-read this document's own named chain, not just
the single capability it unlocks — several capabilities share a root
trigger and should be considered together (e.g., an OCR decision
affects both coverage expansion and the original GTCO/Zenith pilot
anchors).
