-- ============================================================================
-- Seed reference data. Everything marked 'assumed' or with NULL dates is a
-- Phase 1 open question — see docs/PHASE1_DATA_GAPS.md.
-- ============================================================================

INSERT OR IGNORE INTO sources (source_id, name, kind, reliability, base_confidence, notes) VALUES
 (1, 'manual_seed',              'manual_entry', 'unverified', 0.4, 'Phase 1 reference seeding; verify before production use'),
 (2, 'ngx_website_daily',        'exchange_official', 'primary', 0.9, 'ngxgroup.com daily price list / index summary — access method TBC'),
 (3, 'derived_computation',      'derived', 'secondary', 0.6, 'values computed by this system from other stored rows');

-- Index registry. base_date = approximate launch (VERIFY — these bound how far
-- back each backtest regime can reach). weighting per NGX methodology docs (VERIFY).
INSERT OR IGNORE INTO indices (index_code, name, weighting, cap_pct, base_date, base_value, is_total_return, notes) VALUES
 ('NGXASI',      'NGX All-Share Index',      'full_mcap',          NULL, '1984-01-03', 100,    0, 'Benchmark. Full market cap, not float-adjusted (verify).'),
 ('NGX30',       'NGX 30 Index',             'capped_float_mcap',  NULL, '2009-01-01', 1000,   0, 'Top 30 by mcap+liquidity; capping factor to confirm.'),
 ('NGXBNK',      'NGX Banking Index',        'capped_float_mcap',  NULL, '2009-01-01', 1000,   0, '10 most capitalised/liquid banks (verify count & capping).'),
 ('NGXINS',      'NGX Insurance Index',      'capped_float_mcap',  NULL, '2009-01-01', 1000,   0, 'Thinnest sector — expect ADTV constraint to bind hardest here.'),
 ('NGXOILGAS',   'NGX Oil & Gas Index',      'capped_float_mcap',  NULL, '2009-01-01', 1000,   0, 'Aradel listed 2024-10 — membership change mid-sample (verify).'),
 ('NGXINDUSTR',  'NGX Industrial Goods Index','capped_float_mcap', NULL, '2009-07-01', 1000,   0, 'Dominated by Dangote Cement + BUA Cement — near single-stock bet.'),
 ('NGXCNSMRGDS', 'NGX Consumer Goods Index', 'capped_float_mcap',  NULL, '2009-07-01', 1000,   0, ''),
 ('NGXPREMIUM',  'NGX Premium Index',        'capped_float_mcap',  NULL, '2015-08-01', 1000,   0, 'Premium-board only; overlaps Banking/Industrial heavily.'),
 ('NGXPENSION',  'NGX Pension Index',        'capped_float_mcap',  NULL, '2015-07-01', 1000,   0, '40 stocks meeting PenCom criteria (verify).');

-- Assumed NGX retail fee stack (ALL rates 'assumed' — confirm against a real
-- broker contract note; brokerage is a regulatory MAX and is negotiable).
INSERT OR IGNORE INTO cost_schedule (fee_name, side, rate_pct, applies_to, effective_from, confidence, source_id, notes) VALUES
 ('brokerage',  'both', 1.35,  'trade_value',         '2000-01-01', 'assumed', 1, 'Regulatory max; institutional/discount often 0.5-0.75%'),
 ('sec_fee',    'buy',  0.30,  'trade_value',         '2000-01-01', 'assumed', 1, 'SEC fee, buy side only (verify side)'),
 ('ngx_fee',    'sell', 0.30,  'trade_value',         '2000-01-01', 'assumed', 1, 'Exchange fee, sell side only (verify side)'),
 ('cscs_fee',   'both', 0.06,  'trade_value',         '2000-01-01', 'assumed', 1, 'CSCS transaction fee (verify rate and side)'),
 ('stamp_duty', 'both', 0.08,  'trade_value',         '2000-01-01', 'assumed', 1, 'Contract stamp duty'),
 ('vat',        'both', 7.50,  'commission_and_fees', '2020-02-01', 'assumed', 1, 'VAT 7.5% on commission+fees since Feb 2020'),
 ('vat',        'both', 5.00,  'commission_and_fees', '2000-01-01', 'assumed', 1, 'VAT 5% before Feb 2020 (effective_to set below)');

UPDATE cost_schedule SET effective_to = '2020-01-31'
 WHERE fee_name = 'vat' AND effective_from = '2000-01-01';
