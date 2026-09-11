from __future__ import annotations

from pathlib import Path
import os


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
RUNTIME_DIR = Path(os.environ.get("AGENT_DATA_DIR", PROJECT_DIR)).resolve()
DEFAULT_DB_PATH = RUNTIME_DIR / "data" / "historico.sqlite3"
DEFAULT_OUTPUT_DIR = RUNTIME_DIR / "salidas"
DEFAULT_ARCHIVE_DIR = RUNTIME_DIR / "corridas"

EQUIPMENT = [
    "P-MG11", "P-MG12", "P-MG13",
    "P-MG21", "P-MG22", "P-MG23",
    "P-MG31", "P-MG32", "P-MG33",
    "P-MG41", "P-MG42", "P-MG43",
]
EQUIPMENT_SET = set(EQUIPMENT)
ROOM_BY_EQUIPMENT = {tag: int(tag[4]) for tag in EQUIPMENT}
SERIES_BY_EQUIPMENT = {
    tag: "A" if ROOM_BY_EQUIPMENT[tag] <= 2 else "B" for tag in EQUIPMENT
}

CALENDAR_HOURS_EQUIPMENT = 168.0
CALENDAR_HOURS_ROOM = 504.0
CALENDAR_HOURS_SERIES = 1008.0
CALENDAR_HOURS_GLOBAL = 2016.0
