# NGX Size and Liquidity Research Note — Design

## Purpose

Create a two-to-four page static PDF quant research note for technical readers. It
summarises the frozen H-011 Size evidence, H-016 standalone ADTV results, and the
current H-013 semantic-integrity limitation without changing any research record.
It also describes the positive controls and architecture of both the Investment OS
and Alpha research process: frozen fixtures, point-in-time policy, evidence
lineage, governance gates, reproducibility, and paper-only portfolio isolation.

## Evidence treatment

The note will report stored, immutable metrics with source references. H-013 is
not described as high-liquidity robustness: its robust stored code-bucket outcome
is labelled `CODE_BUCKET_HIGH / LOWER_ADTV_BUCKET`, pending additive governance
resolution. H-011 remains confirmed; H-016 remains rejected.

## Structure and charts

The note has: question and conclusion; data/methodology; hypothesis table; stored
empirical metrics; interpretation and risks; next research. Static charts will
show (1) H-013 code-bucket ADTV side and stored excess return separately, and (2)
H-011 versus H-016 stored return/capacity evidence. Captions will distinguish
historical research evidence from model-based or unresolved evidence.

## Boundaries

No new backtest, outcome calculation, H-024 access, data mutation, or claim of
live execution will occur. The report will disclose survivorship, staleness,
corporate-action, capacity, and semantic-label risks.
