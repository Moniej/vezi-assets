# DOL Close-Price Validation — 2026-07-21

Sampled 60 overlap days; parse errors: 0; traded rows joined: 6,115
Print times: 0 of 60 files carry one; intraday prints (<14:30, EXCLUDED from ingestible stats): none

## Close match (|diff| < 0.005) vs equity_prices
- overall (ingestible, early prints excluded): 99.4440%  (6,115 rows)
- incl. early prints (context only): 99.4440%  (6,115 rows)
- 2014-2018: 100.0000%  (2,337 rows)
- 2019+: 99.1001%  (3,778 rows)

### Mismatches (34):
    symbol  file_date  close  px_close
  OKOMUOIL 2022-03-16 142.50    143.50
    PRESCO 2022-03-16 125.00    133.00
 LIVESTOCK 2022-03-16   1.58      1.60
      SCOA 2022-03-16   2.40      2.38
 TRANSCORP 2022-03-16   1.11      1.12
      UACN 2022-03-16  11.00     12.10
      UPDC 2022-03-16   0.95      0.97
        NB 2022-03-16  45.40     44.50
 DANGSUGAR 2022-03-16  16.00     15.80
 HONYFLOUR 2022-03-16   3.74      3.73
  UNILEVER 2022-03-16  13.60     13.50
FIDELITYBK 2022-03-16   2.93      2.98
      GTCO 2022-03-16  26.15     26.20
  JAIZBANK 2022-03-16   0.70      0.71
       UBN 2022-03-16   6.25      6.20
  CORNERST 2022-03-16   0.62      0.58
    LASACO 2022-03-16   1.07      1.04
  NIGERINS 2022-03-16   0.22      0.20
VERITASKAP 2022-03-16   0.22      0.21
     WAPIC 2022-03-16   0.49      0.53
      FCMB 2022-03-16   3.45      3.41
  NGXGROUP 2022-03-16  23.30     23.75
   ROYALEX 2022-03-16   1.02      1.12
      UCAP 2022-03-16  12.50     12.40
    FIDSON 2022-03-16   7.76      7.85
MULTIVERSE 2022-03-16   0.22      0.23
JAPAULGOLD 2022-03-16   0.33      0.34
 REDSTAREX 2022-03-16   3.05      3.00
       UPL 2022-03-16   2.49      2.45
  CAVERTON 2022-03-16   1.31      1.30
       UBA 2022-03-16   8.55      8.50
ZENITHBANK 2022-03-16  26.40     26.45
      FBNH 2022-03-16  11.75     11.95
    SEPLAT 2022-03-16 960.00    930.00

## Coverage (DOL traded rows / pricelist symbols per day)
- median 98.0% | p10 94.5% | min 89.2% (2026-05-04)

## VERDICT: PASS (rule: match >= 99% overall + per era, median coverage >= 90%)