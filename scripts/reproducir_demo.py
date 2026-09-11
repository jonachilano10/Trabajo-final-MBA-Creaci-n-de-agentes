from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
from datetime import date, datetime, time
from pathlib import Path

import openpyxl


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT))

from agente_mantenimiento.analysis import analyze_week  # noqa: E402
from agente_mantenimiento.database import HistoryDatabase  # noqa: E402
from agente_mantenimiento.llm_openai import interpret_week_with_openai  # noqa: E402
from agente_mantenimiento.privacy import validate_no_confidential_data  # noqa: E402
from agente_mantenimiento.provenance import (  # noqa: E402
    runtime_manifest, sha256_file, sha256_json,
)
from agente_mantenimiento.report import generate_report  # noqa: E402


YEAR = 2026
WEEK = 2
START = date(2026, 1, 5)
END = date(2026, 1, 11)
EXPECTED = {
    "maintenance_hours": 4.0,
    "stop_hours": 3.75,
    "stoppage_count": 2,
    "availability": (2016.0 - 4.0 - 3.75) / (2016.0 - 4.0) * 100,
}


def _save_book(path: Path, rows: list[list[object]], *, title_row: bool = False) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Datos"
    if title_row:
        sheet.append(["Tareas técnicas de la semana"])
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def create_synthetic_inputs(directory: Path) -> dict[str, Path]:
    """Create small, non-confidential workbooks matching the production contract."""
    directory.mkdir(parents=True, exist_ok=True)
    notices = directory / "avisos_demo.xlsx"
    notifications = directory / "notificaciones_demo.xlsx"
    maintenance = directory / "tareas_demo.xlsx"
    _save_book(notices, [
        [
            "Fecha de aviso", "Aviso", "Equipo", "Descripcion", "Parada",
            "Duracion de parada", "Orden", "Inicio de averia",
            "Hora de inicio de averia", "Fin de averia", "Hora de fin de averia",
            "Texto ampl", "Causa texto",
        ],
        [
            START, "900001", "P-MG11", "Pérdida de aire en manguera", "x", 2.5,
            "700001", START, time(8, 0), START, time(10, 30),
            "Baja presión del circuito", "Manguera con pérdida documentada",
        ],
        [
            START, "900002", "P-MG31", "Pérdida de aire en conexión", "x", 1.25,
            "700002", START, time(12, 0), START, time(13, 15),
            "Baja presión del circuito", "Conexión floja documentada",
        ],
    ])
    _save_book(notifications, [
        [
            "Orden", "Equipo", "Fecha de inicio real", "Texto de notificacion",
            "Contador", "Trabajo real", "Notificacion final",
        ],
        ["700001", "P-MG11", START, "Se reemplazó la manguera", "0010", 1.0, "x"],
        ["700002", "P-MG31", START, "Se ajustó la conexión", "0010", 0.5, "x"],
    ])
    _save_book(maintenance, [
        ["Equipo", "Nombre de tarea", "Duracion", "Comienzo", "Fin", "Observaciones"],
        [
            "P-MG12", "Inspección programada", 4.0,
            datetime(2026, 1, 6, 8, 0), datetime(2026, 1, 6, 12, 0),
            "Tarea técnica programada",
        ],
    ], title_row=True)
    return {"notices": notices, "notifications": notifications, "maintenance": maintenance}


def _mock_response() -> dict[str, object]:
    findings = {
        "findings": [{
            "relation_type": "cross_bridge",
            "title": "Pérdidas de aire en equipos diferentes",
            "notice_numbers": ["900001", "900002"],
            "confidence": "media",
            "rationale": "Ambos avisos documentan una pérdida de aire; las causas específicas difieren.",
            "human_review": "Confirmar en campo antes de concluir que existe un patrón común.",
        }]
    }
    return {
        "id": "resp_demo_deterministico_sin_red",
        "output_text": json.dumps(findings, ensure_ascii=False),
        "usage": {
            "input_tokens": 100, "output_tokens": 80, "total_tokens": 180,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 20},
        },
    }


def reproduce(evidence_dir: Path) -> dict[str, object]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agente_reproduccion_") as temporary:
        work = Path(temporary)
        inputs = create_synthetic_inputs(work / "entradas")
        validate_no_confidential_data((path, path.name) for path in inputs.values())
        analysis = analyze_week(
            year=YEAR, week=WEEK, start_date=START, end_date=END,
            notices_path=inputs["notices"], notifications_path=inputs["notifications"],
            maintenance_path=inputs["maintenance"],
        )
        database_path = work / "historico_demo.sqlite3"
        database = HistoryDatabase(database_path)
        database.save_analysis(analysis)
        interpret_week_with_openai(
            database_path, year=YEAR, week=WEEK, api_key="demo-no-secret",
            model="gpt-5.4-mini", reasoning_effort="medium",
            transport=lambda body, key: _mock_response(),
        )
        report_path = generate_report(
            database_path, year=YEAR, week=WEEK, output_path=evidence_dir / "reporte_demo.html"
        )
        observed = {
            "period": analysis["period"],
            "global": {
                key: analysis["global"][key] for key in EXPECTED
            },
            "series": analysis["series"],
            "rooms": analysis["rooms"],
            "source_counts": analysis["source_counts"],
            "llm_findings": database.load_report_data(YEAR, WEEK)["llm_findings"],
            "llm_runs": database.list_llm_runs(),
        }
        checks = {
            key: math.isclose(float(observed["global"][key]), float(value), rel_tol=0, abs_tol=1e-10)
            if isinstance(value, float) else observed["global"][key] == value
            for key, value in EXPECTED.items()
        }
        checks.update({
            "base_started_empty": True,
            "one_week_persisted": len(database.list_weeks()) == 1,
            "privacy_validation_passed": True,
            "llm_contract_validated": len(observed["llm_findings"]) == 1,
            "report_generated": report_path.is_file(),
        })
        if not all(checks.values()):
            raise AssertionError(f"La reproducción no coincidió con lo esperado: {checks}")
        observed_path = evidence_dir / "resultado_observado.json"
        observed_path.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        manifest = {
            "purpose": "Reproducción segura y determinística desde una base SQLite vacía",
            "command": "python scripts/reproducir_demo.py",
            "network_used": False,
            "input_data": "Excel sintéticos generados en un directorio temporal y eliminados al finalizar",
            "runtime": runtime_manifest(),
            "reproduction_script_sha256": sha256_file(Path(__file__)),
            "system_prompt_sha256": sha256_file(PROJECT / "prompts" / "system_prompt.md"),
            "expected": EXPECTED,
            "checks": checks,
            "observed_output_sha256": sha256_file(observed_path),
            "report_sha256": sha256_file(report_path),
            "synthetic_input_sha256": {name: sha256_file(path) for name, path in inputs.items()},
            "result": "PASS",
        }
        manifest_path = evidence_dir / "MANIFIESTO_REPRODUCCION.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce el agente con datos sintéticos seguros.")
    parser.add_argument(
        "--evidence-dir", type=Path,
        default=PROJECT / "pruebas" / "evidencia_reproducibilidad",
    )
    args = parser.parse_args()
    manifest = reproduce(args.evidence_dir.resolve())
    print(json.dumps({"estado": manifest["result"], "evidencia": str(args.evidence_dir.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
