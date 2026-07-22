# Fund Alpha — Data Moat Strategy

*Adopted 2026-07-15; objective function revised same day.*

## Objective function (governing everything below)

**Maximize Fund Alpha's expected rate of alpha discovery over the next
decade.** Not: validate the current hypothesis. The database is a permanent
asset of the firm; hypotheses are temporary consumables that the database
generates, feeds, and outlives.

Operationally: every acquisition is justified by **how many future
hypothesis families it enables or improves** — its *generativity* — not by
what any single live hypothesis needs. The unit of account is
Δ(credible hypotheses testable per year), and the dependency map in
`docs/HYPOTHESIS_FAMILY_MAP.md` is where that claim is made auditable:
a dataset's generativity score must be backed by named families, or it
doesn't count.

Two corollaries:

1. **The validation platform is the discovery-rate multiplier; data breadth
   is the bottleneck.** H-001 went from real data to a defensible verdict in
   one working session — the machinery is fast. Every new dataset multiplies
   against that speed. This is why acquisition, not tooling, gets the
   investment from here.
2. **Joins compound.** A dataset that cross-links with existing holdings
   (events × prices × membership × corporate actions, all PIT) is worth more
   than its standalone score; keystone datasets — those appearing in the
   dependency sets of many families — get priority even when any single
   family's payoff is uncertain. This is a portfolio of options, and we buy
   cheap optionality.

## The evaluation question

Every dataset is judged by one question: **could this contain information
the market is underpricing?** — and then by the five-question gate:

1. Is there unique information here?
2. Is it difficult to collect?
3. Is it difficult to maintain?
4. Could it plausibly generate alpha?
5. Is it scalable into a repeatable investment process?

No signal work begins on a dataset until the gate has been answered in
writing (in `configs/dataset_priorities.toml`, which is the living record).

## What is NOT a moat (be honest before spending money)

- **Anything scrapeable in a weekend is not a moat.** MPC dates, index
  levels, Brent — any competent analyst replicates these in days. They are
  *table stakes*: acquire them cheaply because research needs them, but never
  confuse them with an edge.
- **A backtest platform is not a moat.** Ours is good; it is also
  replicable by any disciplined team. It *compounds* a data moat; it isn't
  one.

## The three mechanisms that actually create data moats here

**M1 — Ephemeral capture (time-gated).** Data published daily and then
overwritten or made hard to retrieve: NGX per-stock daily price lists
(volume, value traded, deals), full ticker snapshots, disclosure feeds.
Whoever starts capturing first owns a history that *cannot be bought later
at any price*. The moat deepens automatically every trading day. This is the
highest-conviction mechanism and the reason `scripts/daily_capture.py`
exists and must run every trading day from now on.

**M2 — Point-in-time vintages of public data.** Even fully public data
becomes unreplicable when captured *as it was known*, with announcement
dates and restatement history. Nobody can retroactively reconstruct what the
CBN site said on a given Tuesday, or when a membership change was announced.
Our bitemporal schema turns ordinary scraping into vintage data. Every
capture is stamped; nothing is overwritten.

**M3 — Structured judgment over unstructured primary documents.** Taxonomy-
classified, verification-trailed event records extracted from circular PDFs,
registrar notices, court filings, AGM documents. The cost is analyst
labor and domain judgment — precisely why it's hard to replicate. The event
pipeline (verification trail in `notes`, primary `source_url`, direction
recorded as `unknown` unless ruled) is the factory for this.

## Scoring model

Priority = **EAV × U × R × M × C**, each dimension 1–5:

| Dim | Meaning | 5 means | 1 means |
|---|---|---|---|
| EAV | Expected alpha value | plausibly prices sectors/stocks directly | context only |
| U | Uniqueness | we would likely be the only holders | on every terminal |
| R | Replication difficulty | time-gated or archival archaeology | weekend scrape |
| M | Maintenance (inverted cost) | fully automatable, stable source | ongoing manual labor, fragile source |
| C | Coverage achievable | deep history + full breadth attainable | fragmentary |

Scores are judgment; they live in `configs/dataset_priorities.toml` with a
written rationale per dimension and get revised as probes teach us more.
`scripts/rank_datasets.py` regenerates `reports/data_moat_ranking.md` from
the config — the ranking is reproducible, like everything else here.

**Strategic-necessity override:** a dataset scoring low on moat can still be
acquired early if active research requires it (flagged `necessity = true`).
Table stakes are bought cheaply; they are just never mistaken for moat.

## Standing rules going forward

1. **Capture before you can use.** Ephemeral feeds are archived from today
   even with no consuming hypothesis; storage is cheap, hindsight isn't.
2. **Raw first, structured second.** Every capture stores the raw payload
   (JSON/PDF/HTML) before any parsing, so future re-parsing with better
   taxonomies is always possible.
3. **Provenance or it doesn't exist.** Source, URL, timestamp, confidence on
   every row — unchanged from the research mandate.
4. **Legality and ethics gate.** Respect source terms; flag politically
   sensitive data (e.g. parallel-market FX) for explicit review before
   acquisition. A moat built on data we can't defend holding is a liability.
5. **The five-question gate precedes any signal proposal**, in writing.
