"""Investment Management Layer (2026-08-12, BUILD ASSIGNMENT).

Closes the missing loop: Signal -> Portfolio -> Risk -> Paper Execution ->
Performance -> Attribution -> Decision Journal -> Research Feedback.

PAPER/SIMULATION ONLY. No module in this package connects to a broker,
touches real money, or claims paper performance is live performance. See
db.py's own docstring for the storage-isolation rationale (a dedicated
data/portfolio.sqlite, separate from data/ngx.sqlite and
data/registry.sqlite -- neither existing database is modified by this
package).

alpha_engine.py, engine_full.py, runner.py, and the hypothesis registry
are consumed read-only (via alpha_engine.AlphaEngine.recommendations() and
direct reads of registry.sqlite/ngx.sqlite) and never modified.
"""
