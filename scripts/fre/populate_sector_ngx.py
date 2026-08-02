"""FSI Phase 23: Sector Classification Data (docs/fre_runs/
fsi_phase23_preregistration.md). One-time data-loading script, per the
owner's explicit authorization to introduce NGX's own official sector
classification as reference metadata (not analytical/investment data).

Source: NGX's own "Daily Official List (Equities) For 21/04/2026"
(https://doclib.ngxgroup.com/DownloadsContent/Daily%20Official%20List%20-%20Equities%20for%2021-04-2026.pdf),
a genuine, official, primary-source PDF copyrighted "Nigerian Exchange
(NGX) Limited," organizing every listed equity under NGX's own 13
top-level sector headings and named sub-industries across the Main
Board, Premium Board, and REITCEF sections. Retrieved 2026-08-02.

The mapping below is a literal transcription of that document -- every
(ticker, sector_ngx, sub_industry, board_section) tuple was read
directly from the source PDF's own table rows, never inferred from a
company description or business summary. Only tickers with an exact,
unambiguous match against this platform's own `securities.ticker`
column are included; every other real security (bonds, ETFs, synthetic
placeholders, pre-rename ticker aliases already superseded by Phase
9's own `renamed_from` edges, and real tickers simply absent from this
particular document -- most plausibly delisted/suspended, unconfirmed)
is deliberately left out and therefore stays NULL, disclosed in
fsi_phase23_preregistration.md rather than guessed here.

  PYTHONPATH=src python scripts/fre/populate_sector_ngx.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

SOURCE_DOCUMENT = "NGX Daily Official List (Equities) For 21/04/2026"
SOURCE_URL = ("https://doclib.ngxgroup.com/DownloadsContent/"
              "Daily%20Official%20List%20-%20Equities%20for%2021-04-2026.pdf")
RETRIEVAL_DATE = "2026-08-02"

# (ticker, sector_ngx, sub_industry, board_section) -- transcribed directly
# from the source document's own table rows, verbatim.
SECTOR_MAPPING: list[tuple[str, str, str, str]] = [
    # AGRICULTURE
    ("ELLAHLAKES", "AGRICULTURE", "Crop Production", "Main Board"),
    ("FTNCOCOA", "AGRICULTURE", "Crop Production", "Main Board"),
    ("OKOMUOIL", "AGRICULTURE", "Crop Production", "Main Board"),
    ("PRESCO", "AGRICULTURE", "Crop Production", "Main Board"),
    ("LIVESTOCK", "AGRICULTURE", "Livestock/Animal Specialties", "Main Board"),
    # CONGLOMERATES
    ("CUSTODIAN", "CONGLOMERATES", "Diversified Industries", "Main Board"),
    ("JOHNHOLT", "CONGLOMERATES", "Diversified Industries", "Main Board"),
    ("SCOA", "CONGLOMERATES", "Diversified Industries", "Main Board"),
    ("TRANSCORP", "CONGLOMERATES", "Diversified Industries", "Main Board"),
    ("UACN", "CONGLOMERATES", "Diversified Industries", "Main Board"),
    # CONSTRUCTION/REAL ESTATE
    ("AVAIF", "CONSTRUCTION/REAL ESTATE", "Infrastructure/Heavy Construction", "Main Board"),
    ("CNIF", "CONSTRUCTION/REAL ESTATE", "Infrastructure/Heavy Construction", "Main Board"),
    ("JBERGER", "CONSTRUCTION/REAL ESTATE", "Infrastructure/Heavy Construction", "Main Board"),
    ("MOFIREIF", "CONSTRUCTION/REAL ESTATE", "Infrastructure/Heavy Construction", "Main Board"),
    ("NIDF", "CONSTRUCTION/REAL ESTATE", "Infrastructure/Heavy Construction", "Main Board"),
    ("HMCALL", "CONSTRUCTION/REAL ESTATE", "Real Estate Development", "Main Board"),
    ("UPDC", "CONSTRUCTION/REAL ESTATE", "Real Estate Development", "Main Board"),
    ("NREIT", "CONSTRUCTION/REAL ESTATE", "Real Estate Investment Trusts (REITs)", "Main Board"),
    ("SFSREIT", "CONSTRUCTION/REAL ESTATE", "Real Estate Investment Trusts (REITs)", "REITCEF"),
    ("UHOMREIT", "CONSTRUCTION/REAL ESTATE", "Real Estate Investment Trusts (REITs)", "REITCEF"),
    ("UPDCREIT", "CONSTRUCTION/REAL ESTATE", "Real Estate Investment Trusts (REITs)", "REITCEF"),
    # CONSUMER GOODS
    ("CHAMPION", "CONSUMER GOODS", "Beverages--Brewers/Distillers", "Main Board"),
    ("GOLDBREW", "CONSUMER GOODS", "Beverages--Brewers/Distillers", "Main Board"),
    ("GUINNESS", "CONSUMER GOODS", "Beverages--Brewers/Distillers", "Main Board"),
    ("INTBREW", "CONSUMER GOODS", "Beverages--Brewers/Distillers", "Main Board"),
    ("NB", "CONSUMER GOODS", "Beverages--Brewers/Distillers", "Main Board"),
    ("BUAFOODS", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("DANGSUGAR", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("HONYFLOUR", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("MULTITREX", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("NASCON", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("NNFM", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("UNIONDICON", "CONSUMER GOODS", "Food Products", "Main Board"),
    ("CADBURY", "CONSUMER GOODS", "Food Products--Diversified", "Main Board"),
    ("NESTLE", "CONSUMER GOODS", "Food Products--Diversified", "Main Board"),
    ("ENAMELWA", "CONSUMER GOODS", "Household Durables", "Main Board"),
    ("VITAFOAM", "CONSUMER GOODS", "Household Durables", "Main Board"),
    ("PZ", "CONSUMER GOODS", "Personal/Household Products", "Main Board"),
    ("UNILEVER", "CONSUMER GOODS", "Personal/Household Products", "Main Board"),
    # FINANCIAL SERVICES
    ("ETI", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("FIDELITYBK", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("GTCO", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("STERLINGNG", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("UNITYBNK", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("WEMABANK", "FINANCIAL SERVICES", "Banking", "Main Board"),
    ("UBA", "FINANCIAL SERVICES", "Banking", "Premium Board"),
    ("ZENITHBANK", "FINANCIAL SERVICES", "Banking", "Premium Board"),
    ("AFRINSURE", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("AIICO", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("CONHALLPLC", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("CORNERST", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("FTGINSURE", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("GUINEAINS", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("INTENEGINS", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("LASACO", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("LINKASSURE", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("MANSARD", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("MBENEFIT", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("NEM", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("PRESTIGE", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("REGALINS", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("SOVRENINS", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("STACO", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("SUNUASSUR", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("UNIVINSURE", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("VERITASKAP", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("WAPIC", "FINANCIAL SERVICES", "Insurance Carriers, Brokers and Services", "Main Board"),
    ("NPFMCRFBK", "FINANCIAL SERVICES", "Micro-Finance Banks", "Main Board"),
    ("ABBEYBDS", "FINANCIAL SERVICES", "Mortgage Carriers, Brokers and Services", "Main Board"),
    ("INFINITY", "FINANCIAL SERVICES", "Mortgage Carriers, Brokers and Services", "Main Board"),
    ("AFRIPRUD", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("DEAPCAP", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("FCMB", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("NGXGROUP", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("ROYALEX", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("STANBIC", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("UCAP", "FINANCIAL SERVICES", "Other Financial Institutions", "Main Board"),
    ("ACCESSCORP", "FINANCIAL SERVICES", "Other Financial Institutions", "Premium Board"),
    ("FIRSTHOLDCO", "FINANCIAL SERVICES", "Other Financial Institutions", "Premium Board"),
    # HEALTHCARE
    ("EKOCORP", "HEALTHCARE", "Healthcare Providers", "Main Board"),
    ("MORISON", "HEALTHCARE", "Medical Supplies", "Main Board"),
    ("FIDSON", "HEALTHCARE", "Pharmaceuticals", "Main Board"),
    ("MAYBAKER", "HEALTHCARE", "Pharmaceuticals", "Main Board"),
    ("NEIMETH", "HEALTHCARE", "Pharmaceuticals", "Main Board"),
    ("PHARMDEKO", "HEALTHCARE", "Pharmaceuticals", "Main Board"),
    # ICT
    ("OMATEK", "ICT", "Computers and Peripherals", "Main Board"),
    ("CWG", "ICT", "IT Services", "Main Board"),
    ("NCR", "ICT", "IT Services", "Main Board"),
    ("CHAMS", "ICT", "Processing Systems", "Main Board"),
    ("ETRANZACT", "ICT", "Processing Systems", "Main Board"),
    ("AIRTELAFRI", "ICT", "Telecommunications Services", "Main Board"),
    ("LEGENDINT", "ICT", "Telecommunications Services", "Main Board"),
    ("MTNN", "ICT", "Telecommunications Services", "Premium Board"),
    # INDUSTRIAL GOODS
    ("BERGER", "INDUSTRIAL GOODS", "Building Materials", "Main Board"),
    ("BUACEMENT", "INDUSTRIAL GOODS", "Building Materials", "Main Board"),
    ("CAP", "INDUSTRIAL GOODS", "Building Materials", "Main Board"),
    ("MEYER", "INDUSTRIAL GOODS", "Building Materials", "Main Board"),
    ("PREMPAINTS", "INDUSTRIAL GOODS", "Building Materials", "Main Board"),
    ("DANGCEM", "INDUSTRIAL GOODS", "Building Materials", "Premium Board"),
    ("WAPCO", "INDUSTRIAL GOODS", "Building Materials", "Premium Board"),
    ("AUSTINLAZ", "INDUSTRIAL GOODS", "Electronic and Electrical Products", "Main Board"),
    ("CUTIX", "INDUSTRIAL GOODS", "Electronic and Electrical Products", "Main Board"),
    ("BETAGLAS", "INDUSTRIAL GOODS", "Packaging/Containers", "Main Board"),
    ("TRIPPLEG", "INDUSTRIAL GOODS", "Packaging/Containers", "Main Board"),
    # INVESTMENT
    ("VFDGROUP", "INVESTMENT", "Diversified Industries", "Main Board"),
    # NATURAL RESOURCES
    ("IMG", "NATURAL RESOURCES", "Chemicals", "Main Board"),
    ("ALEX", "NATURAL RESOURCES", "Metals", "Main Board"),
    ("MULTIVERSE", "NATURAL RESOURCES", "Mining Services", "Main Board"),
    ("THOMASWY", "NATURAL RESOURCES", "Paper/Forest Products", "Main Board"),
    # OIL AND GAS
    ("JAPAULGOLD", "OIL AND GAS", "Energy Equipment and Services", "Main Board"),
    ("ARADEL", "OIL AND GAS", "Integrated Oil and Gas Services", "Main Board"),
    ("OANDO", "OIL AND GAS", "Integrated Oil and Gas Services", "Main Board"),
    ("CONOIL", "OIL AND GAS", "Petroleum and Petroleum Products Distributors", "Main Board"),
    ("ETERNA", "OIL AND GAS", "Petroleum and Petroleum Products Distributors", "Main Board"),
    ("TOTAL", "OIL AND GAS", "Petroleum and Petroleum Products Distributors", "Main Board"),
    ("SEPLAT", "OIL AND GAS", "Exploration and Production", "Premium Board"),
    # SERVICES
    ("AFROMEDIA", "SERVICES", "Advertising", "Main Board"),
    ("RTBRISCOE", "SERVICES", "Automobile/Auto Part Retailers", "Main Board"),
    ("REDSTAREX", "SERVICES", "Courier/Freight/Delivery", "Main Board"),
    ("TRANSEXPR", "SERVICES", "Courier/Freight/Delivery", "Main Board"),
    ("TANTALIZER", "SERVICES", "Hospitality", "Main Board"),
    ("IKEJAHOTEL", "SERVICES", "Hotels/Lodging", "Main Board"),
    ("TRANSCOHOT", "SERVICES", "Hotels/Lodging", "Main Board"),
    ("DAARCOMM", "SERVICES", "Media/Entertainment", "Main Board"),
    ("ACADEMY", "SERVICES", "Printing/Publishing", "Main Board"),
    ("LEARNAFRCA", "SERVICES", "Printing/Publishing", "Main Board"),
    ("UPL", "SERVICES", "Printing/Publishing", "Main Board"),
    ("ABCTRANS", "SERVICES", "Road Transportation", "Main Board"),
    ("EUNISELL", "SERVICES", "Specialty", "Main Board"),
    ("NSLTECH", "SERVICES", "Specialty", "Main Board"),
    ("CAVERTON", "SERVICES", "Support and Logistics", "Main Board"),
    ("CILEASING", "SERVICES", "Support and Logistics", "Main Board"),
    ("NAHCO", "SERVICES", "Transport-Related Services", "Main Board"),
    ("SKYAVN", "SERVICES", "Transport-Related Services", "Main Board"),
    # UTILITIES
    ("GEREGU", "UTILITIES", "Electric Power Generation", "Main Board"),
    ("TRANSPOWER", "UTILITIES", "Electric Power Generation", "Main Board"),
]


def populate(con: sqlite3.Connection) -> tuple[int, int]:
    """Applies SECTOR_MAPPING: UPDATEs securities.sector_ngx and INSERTs
    one sector_ngx_provenance row per ticker, only for tickers that
    exist in securities. Returns (updated_count, skipped_count)."""
    updated = 0
    skipped = 0
    for ticker, sector_ngx, sub_industry, board_section in SECTOR_MAPPING:
        exists = con.execute("SELECT 1 FROM securities WHERE ticker = ?", (ticker,)).fetchone()
        if exists is None:
            skipped += 1
            continue
        con.execute("UPDATE securities SET sector_ngx = ? WHERE ticker = ?", (sector_ngx, ticker))
        con.execute(
            "INSERT INTO sector_ngx_provenance (ticker, sector_ngx, sub_industry, board_section, "
            "source_document, source_url, retrieval_date) VALUES (?,?,?,?,?,?,?)",
            (ticker, sector_ngx, sub_industry, board_section, SOURCE_DOCUMENT, SOURCE_URL, RETRIEVAL_DATE),
        )
        updated += 1
    return updated, skipped


def main() -> int:
    backup_path = db.DEFAULT_DB.parent / f"ngx.sqlite.pre_fsi_phase23_sector_ngx_backup_{date.today().isoformat()}"
    shutil.copy(db.DEFAULT_DB, backup_path)
    print(f"Backup written to: {backup_path}")

    db.init_db(db.DEFAULT_DB, seed=False)  # applies schema.sql's new sector_ngx_provenance table

    con = db.connect(db.DEFAULT_DB)
    updated, skipped = populate(con)
    con.commit()
    con.close()

    print(f"Populated sector_ngx + provenance for {updated} tickers ({skipped} in SECTOR_MAPPING "
          f"had no matching securities row -- should be 0).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
