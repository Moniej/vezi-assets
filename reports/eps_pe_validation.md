# EPS / P.E. Extraction Validation — 2026-07-22

Sampled 80 days (2014-06-30..2026-05-04), 6,111 symbol-day rows extracted, 0 file errors.

## Cross-check: EPS x P.E. within 3% of known close
- pass rate: 34.33%  (2,098 / 6,111)
- median |rel error| (passing rows): 0.0011
- coverage: 171 symbols represented

### Worst 20 mismatches:
   symbol  file_date  eps    pe  implied_close  close_used  rel_error
      CAP 2014-12-23 4.50 21.22          95.49       36.10     1.6452
      CAP 2014-09-01 4.50 21.22          95.49       39.05     1.4453
      CAP 2014-06-30 4.50 21.22          95.49       40.00     1.3872
      CAP 2014-10-24 4.50 21.22          95.49       41.00     1.3290
 CHAMPION 2023-03-21 0.02  0.01           0.00        4.90     1.0000
 CHAMPION 2025-07-31 0.06  0.01           0.00       13.90     1.0000
 CHAMPION 2023-01-19 0.02  0.01           0.00        5.00     1.0000
 CHAMPION 2026-05-04 0.06  0.01           0.00       14.25     1.0000
 CHAMPION 2025-11-13 0.06  0.01           0.00       14.50     1.0000
 CHAMPION 2026-01-06 0.06  0.01           0.00       15.00     1.0000
TRANSEXPR 2026-05-04 0.02  0.01           0.00        6.40     1.0000
 NIGERINS 2018-06-19 0.00 88.74           0.00        0.26     1.0000
 CHAMPION 2023-05-30 0.02  0.01           0.00        4.16     1.0000
 CHAMPION 2026-02-25 0.06  0.01           0.00       17.60     1.0000
GUINEAINS 2025-04-14 0.01  0.01           0.00        0.69     0.9999
TRANSEXPR 2025-04-14 0.02  0.01           0.00        2.00     0.9999
 CHAMPION 2021-09-07 0.02  0.01           0.00        2.08     0.9999
 CHAMPION 2024-09-05 0.02  0.01           0.00        2.96     0.9999
GUINEAINS 2026-05-04 0.01  0.01           0.00        1.06     0.9999
 CHAMPION 2021-02-04 0.02  0.01           0.00        3.06     0.9999

## VERDICT: FAIL (rule: pass rate >= 95% on >= 500 rows)