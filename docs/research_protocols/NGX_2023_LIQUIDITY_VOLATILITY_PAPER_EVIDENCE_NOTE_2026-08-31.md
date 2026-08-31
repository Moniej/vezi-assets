# NGX Liquidity/Volatility Paper — Research Evidence and Protocol Note

## Classification

`hypothesis-generating / replication-required`. This note is a Research OS
protocol record, not a validated Fund Alpha conclusion or formal Alpha evidence.
The underlying paper was supplied for research planning; it is not copied into
the immutable Fund Alpha archive by this task.

## Claims recorded from the supplied paper context

- Market/universe: NGX / NGX-30.
- Sample: January 2014 through December 2021, monthly frequency.
- Liquidity construction: depth and breadth combined as a PCA liquidity
  composite.
- Macro construction: inflation and exchange rate composite.
- Method: GARCH(1,1).
- Reported results include liquidity significance, macro significance, and
  volatility persistence.

These are claims of the paper, not independently replicated facts.

## Critique flags retained with the evidence

1. A positive reported `LIQIDX` coefficient conflicts with the paper's
   lower-volatility verbal interpretation.
2. A reported ARCH coefficient is negative.
3. An individually reported GARCH coefficient is above one.
4. Descriptive-statistics table and accompanying text do not match.
5. Unit-root labels are inconsistent.
6. The observational unit is unclear: aggregate versus constituent treatment
   is not adequately distinguished.

## Use restriction

The paper may motivate H-024 only. Fund Alpha must test its independently
defined, PIT-safe ADTV60 shock protocol; it must not import this paper's PCA,
macro construction, coefficients, or conclusions as validated platform output.
