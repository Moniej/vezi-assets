"""Build the small, non-evidence frozen regression databases deterministically."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "fixtures" / "stage1" / "frozen"
SOURCE_HASHES = {
    "ngx.sqlite": "0ea0966b581d43e1f4bc3abf8c15bb0992796cf71b4f9a7c38abed407bfff976",
    "registry.sqlite": "0b30a292a612a314208950230d65dae52d0a0c090145b914b2ea13e9e319e87c",
}
BASELINE_COMMIT = "84df6af27066febb376ce02dd0eea2d06345bfe2"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_ngx(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript((ROOT / "schema" / "schema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO sources(source_id,name,kind,reliability,base_confidence) VALUES (1,'frozen_regression_source','manual_entry','synthetic',1.0)")
        for ticker in ("CAP", "NASCON", "UCAP", "DANGCEM", "GTCO"):
            con.execute("INSERT INTO securities(ticker,name,reporting_currency) VALUES (?,?,?)", (ticker, ticker + ' Fixture', 'NGN'))
        doc_id = 100
        evidence_id = 1000
        fact_rows: list[tuple] = []
        def document(ticker: str) -> int:
            nonlocal doc_id
            doc_id += 1
            con.execute("INSERT INTO documents(doc_id,ticker,doc_type,source_type,filing_date,retrieved_date,local_path,source_confidence,source_id,as_of_date) VALUES (?,?,?,?,?,?,?,?,?,?)", (doc_id,ticker,'financial_statement','filing','2021-05-18','2021-05-18',f'fixture://{ticker}/{doc_id}',1.0,1,'2021-05-18'))
            return doc_id
        def fact(doc: int, fact_id: int, fact_type: str, value: float, start: str | None, end: str, tier: str | None) -> None:
            nonlocal evidence_id
            evidence_id += 1
            con.execute("INSERT INTO evidence(evidence_id,doc_id,quoted_text,source_confidence) VALUES (?,?,?,?)", (evidence_id,doc,'fixture evidence '+fact_type,1.0))
            con.execute("INSERT INTO extracted_facts(fact_id,doc_id,fact_type,description,numeric_value,evidence_id,extraction_confidence,grounding_check,extracted_at,period_start,period_end,period_type,confidence_tier,currency,numeric_consistency_check,tabular_unit_check) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (fact_id,doc,fact_type,'fixture '+fact_type,value,evidence_id,1.0,'passed','2021-05-18T00:00:00Z',start,end,'FY',tier,'NGN','pass','pass'))
        cap = document('CAP')
        fact(cap, 410, 'revenue', 8_737_000_000, '2020-01-01', '2020-12-31', None)
        fact(cap, 411, 'ebit', 1_645_000_000, '2020-01-01', '2020-12-31', 'direct_reported')
        fact(cap, 416, 'liabilities', 2_000_000_000, None, '2020-12-31', 'direct_reported')
        fact(cap, 417, 'equity', 4_000_000_000, None, '2020-12-31', 'direct_reported')
        for i, year in enumerate((2020, 2021, 2022)):
            doc = document('NASCON'); start=f'{year}-01-01'; end=f'{year}-12-31'; base=500+i*100
            fact(doc, base+1, 'revenue', 10_000+i*100, start,end,'direct_reported'); fact(doc,base+2,'net_profit',1_000+i*10,start,end,'direct_reported'); fact(doc,base+3,'cfo',900+i*10,start,end,'direct_reported'); fact(doc,base+4,'liabilities',2_000+i*10,None,end,'direct_reported'); fact(doc,base+5,'equity',4_000+i*10,None,end,'direct_reported')
        for i, year in enumerate((2018,2019,2020,2021,2022)):
            doc=document('UCAP'); fact(doc,800+i*2,'revenue',1_000+i*100,f'{year}-01-01',f'{year}-12-31','direct_reported'); fact(doc,801+i*2,'net_profit',100+i*10,f'{year}-01-01',f'{year}-12-31','direct_reported')
        for ticker in ('DANGCEM','GTCO'):
            for day, close in [('2026-08-05',100.0),('2026-08-06',102.0),('2026-08-07',103.0),('2026-08-10',104.0)]:
                con.execute("INSERT INTO equity_prices(ticker,trade_date,close,volume,source_id,confidence,as_of_date) VALUES (?,?,?,?,?,?,?)", (ticker,day,close,100000,1,1.0,day))
        con.execute("INSERT INTO events(event_id,event_type,announced_date,effective_date,scope,headline,source_id,confidence,as_of_date) VALUES (1,'dividend','2026-03-01','2026-04-01','ticker','fixture corporate action event',1,1.0,'2026-03-01')")
        con.execute("INSERT INTO corporate_actions(action_id,ticker,action_type,declared_date,payment_date,dividend_per_share,currency,source_id,confidence,as_of_date) VALUES (1,'CAP','dividend_cash','2026-03-01','2026-04-01',1.0,'NGN',1,1.0,'2026-03-01')")
        con.commit()
    finally:
        con.close()


def create_registry(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript((ROOT / "schema" / "registry.sql").read_text(encoding="utf-8"))
        rows=[('H-001','Cross-sectional 3-6M price momentum','momentum test','rejected','momentum conclusion'),('H-011','Size: long smallest-cap','size test','confirmed','size conclusion'),('H-016','Liquidity via ADTV','liquidity test','rejected','liquidity conclusion'),('H-017','Dividend payer-status','dividend test','rejected','dividend conclusion')]
        for ident,desc,motiv,status,conclusion in rows:
            con.execute("INSERT INTO hypotheses(hypothesis_id,description,motivation,status,created_at,resolved_at,conclusion,frozen) VALUES (?,?,?,?,?,?,?,?)",(ident,desc,motiv,status,'2026-01-01','2026-02-01',conclusion,1))
        con.commit()
    finally:
        con.close()


def table_counts(path: Path) -> dict[str, int]:
    con=sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True)
    try:
        return {row[0]: con.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name") if con.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]}
    finally: con.close()


def schema_version(path: Path) -> int:
    con = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)
    try:
        return int(con.execute('PRAGMA schema_version').fetchone()[0])
    finally:
        con.close()


def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True)
    for name, maker in [('ngx_regression.sqlite',create_ngx),('registry_regression.sqlite',create_registry)]:
        path=OUT/name
        if path.exists(): os.chmod(path,0o666); path.unlink()
        maker(path); os.chmod(path,0o444)
    manifest={
      'fixture_class':'frozen_regression','fixture_version':'1.0.0','synthetic_non_evidence':True,
      'database_file':'ngx_regression.sqlite','database_sha256':digest(OUT/'ngx_regression.sqlite'),
      'registry_database_file':'registry_regression.sqlite','registry_database_sha256':digest(OUT/'registry_regression.sqlite'),
      'schema_baseline_version':1,'source_baseline_commit':BASELINE_COMMIT,'source_baseline_database_hashes':SOURCE_HASHES,
      'sqlite_schema_versions':{'ngx':schema_version(OUT/'ngx_regression.sqlite'),'registry':schema_version(OUT/'registry_regression.sqlite')},
      'extraction_provenance':'Deterministically selected and structurally recreated regression subset; numeric values retain documented regression values. It is non-evidence and cannot support research or Alpha verdicts.',
      'table_row_counts':table_counts(OUT/'ngx_regression.sqlite'),
      'registry_table_row_counts':table_counts(OUT/'registry_regression.sqlite'),
      'expected_query_outputs':{'financial_ratio_tickers':['CAP','NASCON','UCAP'],'cap_fy2020_debt_to_equity':0.5,'nascon_cfo_to_net_profit_periods':3,'ucap_ebit_margin_periods':5,'corporate_action_count':1}
    }
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__': raise SystemExit(main())
