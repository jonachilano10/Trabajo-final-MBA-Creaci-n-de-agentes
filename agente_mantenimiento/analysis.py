from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import openpyxl

from .config import (
    CALENDAR_HOURS_EQUIPMENT,
    CALENDAR_HOURS_GLOBAL,
    CALENDAR_HOURS_ROOM,
    CALENDAR_HOURS_SERIES,
    EQUIPMENT,
    EQUIPMENT_SET,
    ROOM_BY_EQUIPMENT,
    SERIES_BY_EQUIPMENT,
)


class InputValidationError(ValueError):
    """The input set cannot be processed safely."""


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean(value).lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def canonical_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize_text(value)).strip("_")


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean(value)
    if not text:
        return None
    if " " in text and text[:4].isdigit():
        text = text.split()[0]
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def parse_time(value: Any) -> time | None:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    text = clean(value)
    if not text:
        return None
    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, pattern).time()
        except ValueError:
            continue
    return None


def parse_spanish_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = clean(value)
    text = re.sub(r"^(?:lun|mar|mié|mie|jue|vie|sáb|sab|dom)\s+", "", text, flags=re.I)
    for pattern in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = clean(value).replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_duration(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    match = re.search(r"-?\d+(?:[.,]\d+)?", clean(value))
    return float(match.group().replace(",", ".")) if match else None


def combine_datetime(date_value: Any, time_value: Any) -> datetime | None:
    parsed_date = parse_date(date_value)
    parsed_time = parse_time(time_value)
    return datetime.combine(parsed_date, parsed_time) if parsed_date and parsed_time else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path, header_row: int = 1) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        values = list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if len(values) < header_row:
        raise InputValidationError(f"El archivo {path.name} no contiene la fila de encabezados esperada.")
    headers = [canonical_header(value) for value in values[header_row - 1]]
    rows: list[dict[str, Any]] = []
    for source_row, values_row in enumerate(values[header_row:], start=header_row + 1):
        if not any(clean(value) for value in values_row):
            continue
        row = dict(zip(headers, values_row))
        row["_source_row"] = source_row
        rows.append(row)
    return rows


def require_headers(rows: list[dict[str, Any]], required: set[str], source: str) -> None:
    available = set(rows[0]) if rows else set()
    missing = sorted(required - available)
    if missing:
        raise InputValidationError(
            f"Faltan columnas obligatorias en {source}: {', '.join(missing)}."
        )


def proposed_category(description: str) -> str:
    text = normalize_text(description)
    rules = [
        ("Neumática, aire y compresor", ("perdida de aire", "manguera", "compresor", "sin fuerza")),
        ("Traslación", ("traslac", "no traslada", "se desplaza", "carro")),
        ("Izaje y aparejo", ("izaje", "aparejo", "no sube", "no baja")),
        ("Giro y percha", ("gira", "giro", "percha")),
        ("Herramientas, almeja y cierre", ("almeja", "alicate", "destornillador", "picador", "herramient")),
        ("Mando y control", ("mando", "control", "selectora", "remoto", "manipilador")),
        ("Alimentación eléctrica", ("energia", "electr", "contactor", "fusible", "cable", "luz", "luces")),
        ("Lubricación", ("lubric",)),
        ("Freno", ("freno",)),
        ("Estructura o elemento mecánico", ("ruido", "fatiga", "bulon", "cabezal", "rodamiento", "engranaje")),
    ]
    for category, terms in rules:
        if any(term in text for term in terms):
            return category
    return "Otra / revisión humana"


def _exact_duplicate_issues(source: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signatures = Counter(
        tuple(clean(value) for key, value in row.items() if key != "_source_row") for row in rows
    )
    return [
        {
            "severity": "warning",
            "type": "Registro duplicado exacto",
            "source": source,
            "detail": f"La misma fila aparece {count} veces.",
        }
        for count in signatures.values()
        if count > 1
    ]


def _aggregate(name: str, members: list[str], calendar: float, equipment_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in equipment_rows if row["equipment"] in members]
    maintenance = sum(row["maintenance_hours"] for row in rows)
    stop_hours = sum(row["stop_hours"] for row in rows)
    available = calendar - maintenance
    unavailable = [row["equipment"] for row in rows if row["availability"] is None]
    availability = None if unavailable or available <= 0 else (available - stop_hours) / available * 100
    return {
        "name": name,
        "calendar_hours": calendar,
        "maintenance_hours": maintenance,
        "available_hours": available,
        "stop_hours": stop_hours,
        "stoppage_count": sum(row["stoppage_count"] for row in rows),
        "availability": availability,
        "uncalculable_equipment": unavailable,
    }


def analyze_week(
    *,
    year: int,
    week: int,
    start_date: date,
    end_date: date,
    notices_path: str | Path,
    notifications_path: str | Path,
    maintenance_path: str | Path,
) -> dict[str, Any]:
    """Read the three source workbooks and return deterministic structured results."""
    if (end_date - start_date).days != 6:
        raise InputValidationError("El período debe contener exactamente 7 días, inclusive.")
    paths = {
        "notices": Path(notices_path).resolve(),
        "notifications": Path(notifications_path).resolve(),
        "maintenance": Path(maintenance_path).resolve(),
    }
    missing_files = [str(path) for path in paths.values() if not path.is_file()]
    if missing_files:
        raise InputValidationError("No se encontraron archivos: " + ", ".join(missing_files))
    if len(set(paths.values())) != 3:
        raise InputValidationError("Los tres tipos de entrada deben ser archivos diferentes.")

    notice_rows = load_rows(paths["notices"])
    notification_rows = load_rows(paths["notifications"])
    maintenance_rows = load_rows(paths["maintenance"], header_row=2)
    require_headers(
        notice_rows,
        {"fecha_de_aviso", "aviso", "equipo", "descripcion", "parada", "duracion_de_parada", "orden"},
        paths["notices"].name,
    )
    require_headers(
        notification_rows,
        {"orden", "equipo", "fecha_de_inicio_real", "texto_de_notificacion"},
        paths["notifications"].name,
    )
    require_headers(
        maintenance_rows,
        {"equipo", "nombre_de_tarea", "duracion", "comienzo", "fin"},
        paths["maintenance"].name,
    )

    issues: list[dict[str, Any]] = []
    for source, rows in (
        ("avisos", notice_rows),
        ("notificaciones", notification_rows),
        ("mantenimiento", maintenance_rows),
    ):
        issues.extend(_exact_duplicate_issues(source, rows))

    excluded: dict[str, Counter[str]] = {
        "notices": Counter(),
        "notifications": Counter(),
        "maintenance": Counter(),
    }

    maintenance_events: list[dict[str, Any]] = []
    for row in maintenance_rows:
        equipment = clean(row.get("equipo"))
        if not equipment:
            continue
        if equipment not in EQUIPMENT_SET:
            excluded["maintenance"][equipment] += 1
            continue
        started_at = parse_spanish_datetime(row.get("comienzo"))
        ended_at = parse_spanish_datetime(row.get("fin"))
        hours = parse_duration(row.get("duracion"))
        if not started_at or not ended_at:
            issues.append({
                "severity": "error", "type": "Fecha de mantenimiento inválida",
                "source": "mantenimiento", "source_row": row["_source_row"], "equipment": equipment,
                "detail": "No se pudo interpretar Comienzo o Fin.",
            })
            continue
        if not (start_date <= started_at.date() <= end_date):
            continue
        if hours is None or hours < 0:
            issues.append({
                "severity": "error", "type": "Horas de mantenimiento inválidas",
                "source": "mantenimiento", "source_row": row["_source_row"], "equipment": equipment,
                "detail": f"Duración informada: {clean(row.get('duracion')) or 'vacía'}.",
            })
            continue
        maintenance_events.append({
            "source_row": row["_source_row"], "equipment": equipment,
            "task": clean(row.get("nombre_de_tarea")), "hours": hours,
            "started_at": started_at.isoformat(), "ended_at": ended_at.isoformat(),
            "notes": clean(row.get("observaciones")),
        })

    notifications_by_order: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in notification_rows:
        equipment = clean(row.get("equipo"))
        if equipment not in EQUIPMENT_SET:
            if equipment:
                excluded["notifications"][equipment] += 1
            continue
        notification_date = parse_date(row.get("fecha_de_inicio_real"))
        if notification_date and start_date <= notification_date <= end_date:
            notifications_by_order[clean(row.get("orden"))].append({
                "source_row": row["_source_row"], "equipment": equipment,
                "counter": clean(row.get("contador")),
                "text": clean(row.get("texto_de_notificacion")),
                "actual_work": parse_number(row.get("trabajo_real")),
                "is_final": normalize_text(row.get("notificacion_final")) == "x",
            })

    failures: list[dict[str, Any]] = []
    invalid_stop_equipment: set[str] = set()
    for row in notice_rows:
        equipment = clean(row.get("equipo"))
        if equipment not in EQUIPMENT_SET:
            if equipment:
                excluded["notices"][equipment] += 1
            continue
        notice_date = parse_date(row.get("fecha_de_aviso"))
        if not notice_date or not (start_date <= notice_date <= end_date):
            continue
        has_stop = normalize_text(row.get("parada")) == "x"
        stop_hours = parse_number(row.get("duracion_de_parada"))
        valid_stop = not has_stop or (stop_hours is not None and stop_hours > 0)
        if has_stop and not valid_stop:
            invalid_stop_equipment.add(equipment)
            issues.append({
                "severity": "error", "type": "Parada sin duración válida",
                "source": "avisos", "source_row": row["_source_row"], "equipment": equipment,
                "detail": f"Aviso {clean(row.get('aviso'))}; duración {clean(row.get('duracion_de_parada')) or 'vacía'}.",
            })
        order_number = clean(row.get("orden"))
        candidates = notifications_by_order.get(order_number, [])
        matched = [item for item in candidates if item["equipment"] == equipment]
        mismatched = [item for item in candidates if item["equipment"] != equipment]
        if mismatched:
            issues.append({
                "severity": "error", "type": "Orden coincide pero equipo difiere",
                "source": "vinculación", "source_row": row["_source_row"], "equipment": equipment,
                "detail": f"Orden {order_number}; equipos en notificaciones: {', '.join(sorted({item['equipment'] for item in mismatched}))}.",
            })
        intervention_texts: list[str] = []
        for item in sorted(matched, key=lambda value: (value["counter"], value["source_row"])):
            if item["text"] and item["text"] not in intervention_texts:
                intervention_texts.append(item["text"])
        if order_number and not matched:
            issues.append({
                "severity": "warning", "type": "Orden sin notificación vinculable",
                "source": "vinculación", "source_row": row["_source_row"], "equipment": equipment,
                "detail": f"Aviso {clean(row.get('aviso'))}; orden {order_number}.",
            })
        description = clean(row.get("descripcion"))
        started_at = combine_datetime(row.get("inicio_de_averia"), row.get("hora_de_inicio_de_averia"))
        ended_at = combine_datetime(row.get("fin_de_averia"), row.get("hora_de_fin_de_averia"))
        failures.append({
            "source_row": row["_source_row"], "notice_number": clean(row.get("aviso")),
            "equipment": equipment, "room": ROOM_BY_EQUIPMENT[equipment],
            "series": SERIES_BY_EQUIPMENT[equipment], "description": description,
            "description_normalized": normalize_text(description),
            "extended_text": clean(row.get("texto_ampl")),
            "has_stop": has_stop, "stop_hours": stop_hours if stop_hours is not None else 0.0,
            "valid_stop": valid_stop, "documented_cause": clean(row.get("causa_texto")),
            "order_number": order_number,
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
            "interventions": intervention_texts,
            "linked_notification": bool(matched),
            "category": proposed_category(description),
        })

    stop_failures = [item for item in failures if item["has_stop"] and item["started_at"] and item["ended_at"]]
    for index, first in enumerate(stop_failures):
        first_start, first_end = datetime.fromisoformat(first["started_at"]), datetime.fromisoformat(first["ended_at"])
        for second in stop_failures[index + 1:]:
            if first["equipment"] != second["equipment"]:
                continue
            second_start, second_end = datetime.fromisoformat(second["started_at"]), datetime.fromisoformat(second["ended_at"])
            if max(first_start, second_start) < min(first_end, second_end):
                issues.append({
                    "severity": "warning", "type": "Paradas superpuestas", "source": "avisos",
                    "equipment": first["equipment"],
                    "detail": f"Avisos {first['notice_number']} y {second['notice_number']}.",
                })

    for failure in stop_failures:
        failure_start, failure_end = datetime.fromisoformat(failure["started_at"]), datetime.fromisoformat(failure["ended_at"])
        for maintenance in maintenance_events:
            if failure["equipment"] != maintenance["equipment"]:
                continue
            maintenance_start = datetime.fromisoformat(maintenance["started_at"])
            maintenance_end = datetime.fromisoformat(maintenance["ended_at"])
            if max(failure_start, maintenance_start) < min(failure_end, maintenance_end):
                issues.append({
                    "severity": "warning", "type": "Parada coincidente con mantenimiento",
                    "source": "cruce avisos-mantenimiento", "equipment": failure["equipment"],
                    "detail": f"Aviso {failure['notice_number']}; tarea {maintenance['task']}.",
                })

    equipment_rows: list[dict[str, Any]] = []
    for equipment in EQUIPMENT:
        maintenance_hours = sum(item["hours"] for item in maintenance_events if item["equipment"] == equipment)
        equipment_failures = [item for item in failures if item["equipment"] == equipment]
        stop_hours = sum(
            item["stop_hours"] for item in equipment_failures if item["has_stop"] and item["valid_stop"]
        )
        available_hours = CALENDAR_HOURS_EQUIPMENT - maintenance_hours
        availability = None
        if equipment not in invalid_stop_equipment and available_hours > 0:
            availability = (available_hours - stop_hours) / available_hours * 100
        equipment_rows.append({
            "equipment": equipment, "room": ROOM_BY_EQUIPMENT[equipment],
            "series": SERIES_BY_EQUIPMENT[equipment],
            "calendar_hours": CALENDAR_HOURS_EQUIPMENT,
            "maintenance_hours": maintenance_hours, "available_hours": available_hours,
            "stop_hours": stop_hours,
            "stoppage_count": sum(1 for item in equipment_failures if item["has_stop"]),
            "notice_count": len(equipment_failures), "availability": availability,
            "failure_descriptions": [item["description"] for item in equipment_failures if item["has_stop"]],
        })

    room_rows = [
        _aggregate(
            f"Sala {room}",
            [equipment for equipment in EQUIPMENT if ROOM_BY_EQUIPMENT[equipment] == room],
            CALENDAR_HOURS_ROOM,
            equipment_rows,
        )
        for room in range(1, 5)
    ]
    series_rows = [
        _aggregate(
            f"Serie {series}",
            [equipment for equipment in EQUIPMENT if SERIES_BY_EQUIPMENT[equipment] == series],
            CALENDAR_HOURS_SERIES,
            equipment_rows,
        )
        for series in ("A", "B")
    ]
    global_row = _aggregate("Global", EQUIPMENT, CALENDAR_HOURS_GLOBAL, equipment_rows)

    return {
        "period": {
            "year": year, "week": week, "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "sources": {
            key: {"name": path.name, "sha256": file_sha256(path)} for key, path in paths.items()
        },
        "source_counts": {
            "notices": len(notice_rows), "notifications": len(notification_rows),
            "maintenance": len(maintenance_rows),
        },
        "excluded": {key: dict(value) for key, value in excluded.items()},
        "equipment": equipment_rows,
        "rooms": room_rows,
        "series": series_rows,
        "global": global_row,
        "failures": failures,
        "maintenance_events": maintenance_events,
        "validation_issues": issues,
    }
