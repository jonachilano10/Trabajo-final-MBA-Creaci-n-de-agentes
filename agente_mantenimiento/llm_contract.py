from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import HistoryDatabase


ALLOWED_RELATION_TYPES = {"same_bridge", "cross_bridge"}
ALLOWED_CONFIDENCE = {"baja", "media", "alta"}
FINDING_FIELDS = {
    "relation_type", "title", "notice_numbers", "confidence", "rationale", "human_review"
}
MAX_PREVIOUS_WEEKS = 6


def _context_periods(connection: Any, year: int | None, week: int | None) -> list[tuple[int, int]]:
    if year is None or week is None:
        latest = connection.execute(
            "SELECT year, week FROM weeks ORDER BY year DESC, week DESC LIMIT 1"
        ).fetchone()
        if latest is None:
            return []
        year, week = int(latest["year"]), int(latest["week"])
    rows = connection.execute(
        """
        SELECT year, week FROM weeks
        WHERE year < ? OR (year = ? AND week <= ?)
        ORDER BY year DESC, week DESC
        LIMIT ?
        """,
        (year, year, week, MAX_PREVIOUS_WEEKS + 1),
    ).fetchall()
    return [(int(row["year"]), int(row["week"])) for row in reversed(rows)]


class LLMFindingValidationError(ValueError):
    """Raised when an LLM response does not satisfy the read-only contract."""


def build_llm_context(
    database_path: str | Path, *, year: int | None = None, week: int | None = None
) -> dict[str, Any]:
    """Build facts for semantic interpretation without exposing calculated metrics."""
    database = HistoryDatabase(database_path)
    database.initialize()
    with database.connect() as connection:
        periods = _context_periods(connection, year, week)
        if not periods:
            rows = []
        else:
            conditions = " OR ".join("(w.year = ? AND w.week = ?)" for _ in periods)
            parameters = [value for period in periods for value in period]
            rows = connection.execute(
                f"""
                SELECT w.year, w.week, f.notice_number, f.equipment, f.room, f.series,
                       f.description, f.extended_text, f.documented_cause,
                       f.interventions_json, f.category
                FROM failure_events f
                JOIN weeks w ON w.id = f.week_id
                WHERE f.has_stop = 1 AND ({conditions})
                ORDER BY w.year, w.week, f.equipment, f.source_row
                """,
                parameters,
            ).fetchall()
    return {
        "report_period": {"year": year, "week": week},
        "history_window": {
            "maximum_previous_weeks": MAX_PREVIOUS_WEEKS,
            "included_periods": [{"year": y, "week": w} for y, w in periods],
        },
        "contract": {
            "purpose": "Interpretar texto y proponer relaciones entre fallas.",
            "forbidden": [
                "recalcular o modificar métricas",
                "inventar causas, intervenciones, avisos o valores",
                "afirmar causalidad sin evidencia documental",
            ],
            "required_output_fields": sorted(FINDING_FIELDS),
            "relation_types": sorted(ALLOWED_RELATION_TYPES),
            "confidence_values": sorted(ALLOWED_CONFIDENCE),
        },
        "failure_facts": [
            {
                "year": row["year"], "week": row["week"],
                "notice_number": row["notice_number"], "equipment": row["equipment"],
                "room": row["room"], "series": row["series"],
                "description": row["description"], "extended_text": row["extended_text"],
                "documented_cause": row["documented_cause"],
                "interventions": json.loads(row["interventions_json"]),
                "python_candidate_category": row["category"],
            }
            for row in rows
        ],
    }


def export_llm_context(
    database_path: str | Path,
    output_path: str | Path,
    *,
    year: int | None = None,
    week: int | None = None,
) -> Path:
    """Export only source facts needed to relate failures; calculations stay in Python/SQLite."""
    payload = build_llm_context(database_path, year=year, week=week)
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def validate_llm_payload(
    database_path: str | Path, payload: dict[str, Any], *,
    year: int | None = None, week: int | None = None,
) -> list[dict[str, Any]]:
    """Validate narrative output and reject calculated or invented fields."""
    if not isinstance(payload, dict) or set(payload) != {"findings"}:
        raise LLMFindingValidationError("El archivo debe contener únicamente la clave 'findings'.")
    findings = payload["findings"]
    if not isinstance(findings, list):
        raise LLMFindingValidationError("'findings' debe ser una lista.")

    database = HistoryDatabase(database_path)
    database.initialize()
    with database.connect() as connection:
        periods = _context_periods(connection, year, week)
        where = ""
        parameters: list[Any] = []
        if year is not None and week is not None:
            conditions = " OR ".join("(w.year = ? AND w.week = ?)" for _ in periods)
            where = f" WHERE {conditions}" if conditions else " WHERE 0"
            parameters = [value for period in periods for value in period]
        known_notices = {
            str(row[0]) for row in connection.execute(
                "SELECT f.notice_number FROM failure_events f JOIN weeks w ON w.id = f.week_id" + where,
                parameters,
            )
        }

    validated: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict) or set(finding) != FINDING_FIELDS:
            raise LLMFindingValidationError(
                f"Hallazgo {index}: campos inválidos. No se aceptan métricas ni campos adicionales."
            )
        relation_type = finding["relation_type"]
        confidence = finding["confidence"]
        notices = finding["notice_numbers"]
        if relation_type not in ALLOWED_RELATION_TYPES:
            raise LLMFindingValidationError(f"Hallazgo {index}: relation_type inválido.")
        if confidence not in ALLOWED_CONFIDENCE:
            raise LLMFindingValidationError(f"Hallazgo {index}: confidence inválida.")
        if not isinstance(notices, list) or len(set(map(str, notices))) < 2:
            raise LLMFindingValidationError(f"Hallazgo {index}: se requieren al menos dos avisos.")
        notices = [str(value).strip() for value in notices]
        unknown = sorted(set(notices) - known_notices)
        if unknown:
            raise LLMFindingValidationError(
                f"Hallazgo {index}: avisos inexistentes en la base: {', '.join(unknown)}."
            )
        if any(not isinstance(finding[field], str) or not finding[field].strip()
               for field in ("title", "rationale", "human_review")):
            raise LLMFindingValidationError(f"Hallazgo {index}: los textos no pueden estar vacíos.")
        validated.append({**finding, "notice_numbers": notices})
    return validated


def import_llm_findings(
    database_path: str | Path,
    input_path: str | Path,
    *,
    year: int | None = None,
    week: int | None = None,
) -> int:
    """Validate and store narrative findings without accepting calculated values."""
    database = HistoryDatabase(database_path)
    if year is None or week is None:
        weeks = database.list_weeks()
        if not weeks:
            raise LLMFindingValidationError("No existe una semana donde guardar los hallazgos.")
        year, week = weeks[-1]["year"], weeks[-1]["week"]
    if not database.week_exists(year, week):
        raise LLMFindingValidationError(f"La semana {week}/{year} no existe en la base.")
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validated = validate_llm_payload(database_path, payload, year=year, week=week)
    return database.replace_llm_findings(validated, year=year, week=week)
