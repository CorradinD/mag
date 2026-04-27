from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_path: Path
    offers_dir: Path
    backup_dir: Path
    sheet_name: str
    sku_column: str
    description_column: str
    quantity_column: str
    price_column: str
    data_start_row: int


def get_settings() -> Settings:
    data_dir = BASE_DIR / "data"
    offers_dir = Path(os.getenv("MAG_OFFERS_DIR", data_dir / "offerte"))
    backup_dir = Path(os.getenv("MAG_BACKUP_DIR", data_dir / "backup"))
    return Settings(
        database_path=Path(os.getenv("MAG_DATABASE", data_dir / "magazzino.sqlite3")),
        offers_dir=offers_dir,
        backup_dir=backup_dir,
        sheet_name=os.getenv("MAG_EXCEL_SHEET", "Offerta"),
        sku_column=os.getenv("MAG_EXCEL_SKU_COLUMN", "A"),
        description_column=os.getenv("MAG_EXCEL_DESCRIPTION_COLUMN", "B"),
        quantity_column=os.getenv("MAG_EXCEL_QUANTITY_COLUMN", "C"),
        price_column=os.getenv("MAG_EXCEL_PRICE_COLUMN", "D"),
        data_start_row=int(os.getenv("MAG_EXCEL_DATA_START_ROW", "2")),
    )

