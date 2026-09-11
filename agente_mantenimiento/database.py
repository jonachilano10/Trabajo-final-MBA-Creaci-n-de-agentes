from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator


class DuplicateWeekError(RuntimeError):
    """Raised when the requested year/week already exists."""


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS weeks (
    id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sources_json TEXT NOT NULL,
    source_counts_json TEXT NOT NULL,
    excluded_json TEXT NOT NULL,
    global_calendar_hours REAL NOT NULL,
    global_maintenance_hours REAL NOT NULL,
    global_available_hours REAL NOT NULL,
    global_stop_hours REAL NOT NULL,
    global_stoppage_count INTEGER NOT NULL,
    global_availability REAL,
    UNIQUE(year, week)
);

CREATE TABLE IF NOT EXISTS equipment_week (
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    equipment TEXT NOT NULL,
    room INTEGER NOT NULL,
    series TEXT NOT NULL,
    calendar_hours REAL NOT NULL,
    maintenance_hours REAL NOT NULL,
    available_hours REAL NOT NULL,
    stop_hours REAL NOT NULL,
    stoppage_count INTEGER NOT NULL,
    notice_count INTEGER NOT NULL,
    availability REAL,
    failure_descriptions_json TEXT NOT NULL,
    PRIMARY KEY (week_id, equipment)
);

CREATE TABLE IF NOT EXISTS aggregate_week (
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK(level IN ('room', 'series')),
    aggregate_key TEXT NOT NULL,
    calendar_hours REAL NOT NULL,
    maintenance_hours REAL NOT NULL,
    available_hours REAL NOT NULL,
    stop_hours REAL NOT NULL,
    stoppage_count INTEGER NOT NULL,
    availability REAL,
    uncalculable_equipment_json TEXT NOT NULL,
    PRIMARY KEY (week_id, level, aggregate_key)
);

CREATE TABLE IF NOT EXISTS failure_events (
    id INTEGER PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    notice_number TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    equipment TEXT NOT NULL,
    room INTEGER NOT NULL,
    series TEXT NOT NULL,
    description TEXT NOT NULL,
    description_normalized TEXT NOT NULL,
    extended_text TEXT NOT NULL,
    has_stop INTEGER NOT NULL,
    stop_hours REAL NOT NULL,
    valid_stop INTEGER NOT NULL,
    documented_cause TEXT NOT NULL,
    order_number TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    interventions_json TEXT NOT NULL,
    linked_notification INTEGER NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(week_id, notice_number)
);

CREATE TABLE IF NOT EXISTS maintenance_events (
    id INTEGER PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    source_row INTEGER NOT NULL,
    equipment TEXT NOT NULL,
    task TEXT NOT NULL,
    hours REAL NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_issues (
    id INTEGER PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    source TEXT NOT NULL,
    source_row INTEGER,
    equipment TEXT,
    detail TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_findings (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report_year INTEGER NOT NULL,
    report_week INTEGER NOT NULL,
    relation_type TEXT NOT NULL CHECK(relation_type IN ('same_bridge', 'cross_bridge')),
    title TEXT NOT NULL,
    notice_numbers_json TEXT NOT NULL,
    confidence TEXT NOT NULL,
    rationale TEXT NOT NULL,
    human_review TEXT NOT NULL,
    UNIQUE(report_year, report_week, relation_type, title, notice_numbers_json)
);

CREATE TABLE IF NOT EXISTS llm_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report_year INTEGER NOT NULL,
    report_week INTEGER NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    response_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    input_cost_usd REAL NOT NULL,
    cached_input_cost_usd REAL NOT NULL,
    output_cost_usd REAL NOT NULL,
    total_cost_usd REAL NOT NULL,
    price_input_per_million REAL,
    price_cached_input_per_million REAL,
    price_output_per_million REAL,
    pricing_effective_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_failure_week_equipment ON failure_events(week_id, equipment);
CREATE INDEX IF NOT EXISTS idx_failure_normalized ON failure_events(description_normalized);
CREATE INDEX IF NOT EXISTS idx_equipment_history ON equipment_week(equipment, week_id);
CREATE INDEX IF NOT EXISTS idx_llm_runs_week ON llm_runs(report_year, report_week);
PRAGMA user_version = 3;
"""


class HistoryDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(llm_findings)")
            }
            if "report_year" not in columns:
                connection.executescript(
                    """
                    ALTER TABLE llm_findings RENAME TO llm_findings_legacy;
                    CREATE TABLE llm_findings (
                        id INTEGER PRIMARY KEY,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        report_year INTEGER NOT NULL,
                        report_week INTEGER NOT NULL,
                        relation_type TEXT NOT NULL CHECK(relation_type IN ('same_bridge', 'cross_bridge')),
                        title TEXT NOT NULL,
                        notice_numbers_json TEXT NOT NULL,
                        confidence TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        human_review TEXT NOT NULL,
                        UNIQUE(report_year, report_week, relation_type, title, notice_numbers_json)
                    );
                    INSERT INTO llm_findings (
                        id, created_at, report_year, report_week, relation_type, title,
                        notice_numbers_json, confidence, rationale, human_review
                    )
                    SELECT l.id, l.created_at,
                           COALESCE((SELECT year FROM weeks ORDER BY year DESC, week DESC LIMIT 1), 0),
                           COALESCE((SELECT week FROM weeks ORDER BY year DESC, week DESC LIMIT 1), 0),
                           l.relation_type, l.title, l.notice_numbers_json, l.confidence,
                           l.rationale, l.human_review
                    FROM llm_findings_legacy l;
                    DROP TABLE llm_findings_legacy;
                    PRAGMA user_version = 2;
                    """
                )

    def save_analysis(self, analysis: dict[str, Any]) -> int:
        self.initialize()
        period = analysis["period"]
        global_row = analysis["global"]
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT id FROM weeks WHERE year = ? AND week = ?",
                (period["year"], period["week"]),
            ).fetchone()
            if duplicate:
                raise DuplicateWeekError(
                    f"La semana {period['week']}/{period['year']} ya está cargada. No se realizaron cambios."
                )
            cursor = connection.execute(
                """
                INSERT INTO weeks (
                    year, week, start_date, end_date, sources_json, source_counts_json,
                    excluded_json, global_calendar_hours, global_maintenance_hours,
                    global_available_hours, global_stop_hours, global_stoppage_count,
                    global_availability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    period["year"], period["week"], period["start_date"], period["end_date"],
                    json.dumps(analysis["sources"], ensure_ascii=False, sort_keys=True),
                    json.dumps(analysis["source_counts"], ensure_ascii=False, sort_keys=True),
                    json.dumps(analysis["excluded"], ensure_ascii=False, sort_keys=True),
                    global_row["calendar_hours"], global_row["maintenance_hours"],
                    global_row["available_hours"], global_row["stop_hours"],
                    global_row["stoppage_count"], global_row["availability"],
                ),
            )
            week_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO equipment_week (
                    week_id, equipment, room, series, calendar_hours, maintenance_hours,
                    available_hours, stop_hours, stoppage_count, notice_count, availability,
                    failure_descriptions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        week_id, row["equipment"], row["room"], row["series"],
                        row["calendar_hours"], row["maintenance_hours"], row["available_hours"],
                        row["stop_hours"], row["stoppage_count"], row["notice_count"],
                        row["availability"], json.dumps(row["failure_descriptions"], ensure_ascii=False),
                    )
                    for row in analysis["equipment"]
                ],
            )
            aggregate_values = []
            for level, rows, prefix in (
                ("room", analysis["rooms"], "Sala "),
                ("series", analysis["series"], "Serie "),
            ):
                for row in rows:
                    aggregate_values.append((
                        week_id, level, row["name"].removeprefix(prefix), row["calendar_hours"],
                        row["maintenance_hours"], row["available_hours"], row["stop_hours"],
                        row["stoppage_count"], row["availability"],
                        json.dumps(row["uncalculable_equipment"], ensure_ascii=False),
                    ))
            connection.executemany(
                """
                INSERT INTO aggregate_week (
                    week_id, level, aggregate_key, calendar_hours, maintenance_hours,
                    available_hours, stop_hours, stoppage_count, availability,
                    uncalculable_equipment_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                aggregate_values,
            )
            connection.executemany(
                """
                INSERT INTO failure_events (
                    week_id, notice_number, source_row, equipment, room, series, description,
                    description_normalized, extended_text, has_stop, stop_hours, valid_stop,
                    documented_cause, order_number, started_at, ended_at, interventions_json,
                    linked_notification, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        week_id, row["notice_number"], row["source_row"], row["equipment"],
                        row["room"], row["series"], row["description"], row["description_normalized"],
                        row["extended_text"], int(row["has_stop"]), row["stop_hours"],
                        int(row["valid_stop"]), row["documented_cause"], row["order_number"],
                        row["started_at"], row["ended_at"],
                        json.dumps(row["interventions"], ensure_ascii=False),
                        int(row["linked_notification"]), row["category"],
                    )
                    for row in analysis["failures"]
                ],
            )
            connection.executemany(
                """
                INSERT INTO maintenance_events (
                    week_id, source_row, equipment, task, hours, started_at, ended_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        week_id, row["source_row"], row["equipment"], row["task"], row["hours"],
                        row["started_at"], row["ended_at"], row["notes"],
                    )
                    for row in analysis["maintenance_events"]
                ],
            )
            connection.executemany(
                """
                INSERT INTO validation_issues (
                    week_id, severity, issue_type, source, source_row, equipment, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        week_id, row.get("severity", "warning"), row["type"], row["source"],
                        row.get("source_row"), row.get("equipment"), row.get("detail", ""),
                    )
                    for row in analysis["validation_issues"]
                ],
            )
            connection.commit()
            return week_id

    def week_exists(self, year: int, week: int) -> bool:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM weeks WHERE year = ? AND week = ?", (year, week)
            ).fetchone() is not None

    def list_weeks(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM weeks ORDER BY year, week"
            ).fetchall()
            return [dict(row) for row in rows]

    def load_report_data(self, current_year: int, current_week: int) -> dict[str, Any]:
        self.initialize()
        with self.connect() as connection:
            current = connection.execute(
                "SELECT * FROM weeks WHERE year = ? AND week = ?", (current_year, current_week)
            ).fetchone()
            if not current:
                raise KeyError(f"No existe la semana {current_week}/{current_year} en la base.")
            current_id = current["id"]
            weeks = [dict(row) for row in connection.execute(
                "SELECT * FROM weeks ORDER BY year, week"
            ).fetchall()]
            equipment = [dict(row) for row in connection.execute(
                """
                SELECT w.year, w.week, w.start_date, w.end_date, e.*
                FROM equipment_week e JOIN weeks w ON w.id = e.week_id
                ORDER BY w.year, w.week, e.equipment
                """
            ).fetchall()]
            aggregates = [dict(row) for row in connection.execute(
                """
                SELECT w.year, w.week, w.start_date, w.end_date, a.*
                FROM aggregate_week a JOIN weeks w ON w.id = a.week_id
                ORDER BY w.year, w.week, a.level, a.aggregate_key
                """
            ).fetchall()]
            failures = [dict(row) for row in connection.execute(
                """
                SELECT w.year, w.week, w.start_date, w.end_date, f.*
                FROM failure_events f JOIN weeks w ON w.id = f.week_id
                ORDER BY w.year, w.week, f.equipment, f.source_row
                """
            ).fetchall()]
            current_issues = [dict(row) for row in connection.execute(
                "SELECT * FROM validation_issues WHERE week_id = ? ORDER BY id", (current_id,)
            ).fetchall()]
            findings = [dict(row) for row in connection.execute(
                """
                SELECT * FROM llm_findings
                WHERE report_year = ? AND report_week = ?
                ORDER BY created_at, id
                """,
                (current_year, current_week),
            ).fetchall()]
        for row in failures:
            row["interventions"] = json.loads(row.pop("interventions_json"))
        for row in findings:
            row["notice_numbers"] = json.loads(row.pop("notice_numbers_json"))
        return {
            "current": dict(current), "weeks": weeks, "equipment_history": equipment,
            "aggregate_history": aggregates, "failures": failures,
            "current_issues": current_issues, "llm_findings": findings,
        }

    def replace_llm_findings(
        self, findings: Iterable[dict[str, Any]], *, year: int, week: int
    ) -> int:
        self.initialize()
        rows = list(findings)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM llm_findings WHERE report_year = ? AND report_week = ?",
                (year, week),
            )
            connection.executemany(
                """
                INSERT INTO llm_findings (
                    report_year, report_week, relation_type, title, notice_numbers_json,
                    confidence, rationale, human_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        year, week, row["relation_type"], row["title"],
                        json.dumps(sorted(row["notice_numbers"]), ensure_ascii=False),
                        row["confidence"], row["rationale"], row["human_review"],
                    )
                    for row in rows
                ],
            )
            connection.commit()
        return len(rows)

    def save_llm_run(self, run: dict[str, Any]) -> int:
        self.initialize()
        columns = (
            "report_year", "report_week", "model", "reasoning_effort", "response_id",
            "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens",
            "total_tokens", "input_cost_usd", "cached_input_cost_usd", "output_cost_usd",
            "total_cost_usd", "price_input_per_million",
            "price_cached_input_per_million", "price_output_per_million",
            "pricing_effective_date",
        )
        with self.connect() as connection:
            cursor = connection.execute(
                f"INSERT INTO llm_runs ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                tuple(run[column] for column in columns),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_llm_runs(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM llm_runs ORDER BY created_at DESC, id DESC"
            ).fetchall()]
