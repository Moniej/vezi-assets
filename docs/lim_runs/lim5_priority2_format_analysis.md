# LIM-5 Priority 2 — Prompt/Response Format: Memorization vs. Learning

## Method

Ran the LIM-4 checkpoint (`c52db6e1-...checkpoint-12`, trained on
`entity_recognition-v1.1.0`) on real **training-set** inputs (never
evaluated before — LIM-3/4's benchmark only ever used the held-out `test`
split) and compared outputs to `expected_output`. If the model had
memorized verbatim per-example answers, it would reproduce each training
example's specific target. If it had learned nothing, output would be
unrelated to context. What actually happened is neither.

## Decisive evidence: three examples share one context, one generation

`entity_recognition:1`, `:2`, and `:4` all have the **identical** context
(`{"ticker": null, "filing_ticker": "GTCO", "filing_date": "2024-07-15",
"filing_doc_type": "rights_capital"}` — the residual context-collision
group flagged in Priority 1) but three **different** expected outputs
(`GTCO`/company, `GTBank Nigeria`/competitor_mention, `GTCO non-banking
subsidiaries`/competitor_mention). Under greedy decoding, the checkpoint
produced the **exact same generation for all three**:

```
{"named_entities": [{"entity": "GTCO", "type": "ticker", "confidence": 1},
                    {"entity": "GTCO", "type": "filing_ticker", "confidence": 1}]}
```

**This is conclusive, not suggestive: verbatim memorization is
impossible here by construction** — the same input cannot produce three
different memorized outputs. What the model actually learned is a
shallow, generalizing heuristic: *echo the filing's own ticker as "the"
entity*. That heuristic happens to score correctly for `:1` (whose answer
IS the filing's own ticker) and wrong for `:2`/`:4` (whose answers are
different entities the context never distinguishes) — directly
reproducing, under controlled conditions, the exact context-collision
defect Priority 1 quantified from the data side.

## Other findings from the same run

- **`entity_recognition:5`**: correctly identified the right entity
  (`REDSTAREX`) but invented schema fields that don't exist anywhere in
  `expected_output` or any dataset type's schema (`"SEC Form 12B-25"`,
  `"entity_class": "Exchange"`, `"entity_subclass": "REIT"`) — the model
  has not anchored on the *exact* target key vocabulary, only a general
  "structured entity info" shape.
- **`entity_recognition:6`**: after a plausible answer, generation
  continued past the intended response into a **fabricated new training
  example** (`"### Instruction:\n...### Context:\n{"ticker": "AAPL"...`)
  — the same base-model Alpaca-template-completion leakage documented in
  LIM-3's original diagnosis, still present after the LIM-4 masking fix.
  Masking fixed *what gets supervised during training*; it does not by
  itself stop the base model from continuing to generate past a natural
  stopping point at *inference* time.

## Answer to Priority 2's question

The model is learning **some real structure** — it consistently
produces JSON, consistently includes an entity-like field, and
consistently draws the entity from the given context rather than
generating unrelated content. It is **not** memorizing formatting or
verbatim answers (disproven directly, not inferred). But it has **not**
learned the *actual* task (identify the specific, possibly non-filer
entity being asked about) because — per Priority 1 — the training data's
context frequently doesn't contain the information needed to distinguish
that from the filer's own ticker. The model found the best available
shortcut given the data, which is exactly what a properly-functioning
optimizer is supposed to do; the defect is in the data, not in whether
training "worked."

## Smallest evidence-backed prompt improvements

1. **Do not change the `### Instruction/Context/Response` template** —
   nothing in this evidence implicates the template shape itself; the
   defect is context content (Priority 1), not prompt wording.
2. **Add a hard stop sequence at generation time** (`"### Instruction:"` /
   `"### Context:"`, or simply the EOS token id passed as `eos_token_id`
   to `generate()`) to truncate the observed template-completion leakage
   before it reaches any downstream JSON parser — a generation-time fix,
   not a retraining change, directly motivated by the `:6` observation
   above.
3. **For any dataset type going forward, context must include whatever
   distinguishes the correct answer from the input's own metadata** — the
   generalizable form of Priority 1's finding #2/#3. This is a data
   -export requirement, not a prompt-template change.

No larger prompt-template redesign is supported by this evidence — the
smallest, targeted fix (a generation stop-sequence) is what the data
actually calls for.
