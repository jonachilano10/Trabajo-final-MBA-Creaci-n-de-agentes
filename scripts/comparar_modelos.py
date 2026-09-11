from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT))

from agente_mantenimiento.database import HistoryDatabase  # noqa: E402
from agente_mantenimiento.llm_openai import interpret_week_with_openai  # noqa: E402
from agente_mantenimiento.provenance import runtime_manifest, sha256_file  # noqa: E402


DEFAULT_CONFIGURATIONS = (
    ("gpt-5.4-nano", "medium"),
    ("gpt-5.4-mini", "medium"),
    ("gpt-5.4", "medium"),
)


def parse_configuration(value: str) -> tuple[str, str]:
    try:
        model, effort = value.rsplit(":", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Usá MODELO:NIVEL, por ejemplo gpt-5.4-mini:medium") from error
    if effort not in {"none", "low", "medium", "high", "xhigh"}:
        raise argparse.ArgumentTypeError(f"Nivel no permitido: {effort}")
    return model, effort


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compara configuraciones del LLM sobre el mismo historial sin modificar la base oficial."
    )
    parser.add_argument("--db", type=Path, required=True, help="Base SQLite con las semanas a comparar.")
    parser.add_argument("--anio", type=int, default=2026)
    parser.add_argument("--semanas", type=int, nargs="+", default=[29, 36])
    parser.add_argument(
        "--configuracion", type=parse_configuration, action="append", dest="configurations",
        help="Repetible. Formato MODELO:NIVEL.",
    )
    parser.add_argument(
        "--salida", type=Path, default=PROJECT / "pruebas" / "comparacion_modelos_real"
    )
    parser.add_argument(
        "--confirmar-pruebas-pagas", action="store_true",
        help="Obligatorio: cada combinación realiza una llamada real a la API.",
    )
    args = parser.parse_args()
    if not args.confirmar_pruebas_pagas:
        parser.error("Falta --confirmar-pruebas-pagas. No se harán llamadas por accidente.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Falta OPENAI_API_KEY en el entorno.")
    database_path = args.db.resolve()
    if not database_path.is_file():
        parser.error(f"No existe la base: {database_path}")
    configurations = args.configurations or list(DEFAULT_CONFIGURATIONS)
    source_db = HistoryDatabase(database_path)
    available = {(int(row["year"]), int(row["week"])) for row in source_db.list_weeks()}
    missing = [(args.anio, week) for week in args.semanas if (args.anio, week) not in available]
    if missing:
        parser.error("Semanas ausentes en la base: " + ", ".join(f"{week}/{year}" for year, week in missing))

    output_dir = args.salida.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    for week in args.semanas:
        for model, effort in configurations:
            with tempfile.TemporaryDirectory(prefix="comparacion_llm_") as temporary:
                temporary_db = Path(temporary) / "comparacion.sqlite3"
                shutil.copy2(database_path, temporary_db)
                temporary_history = HistoryDatabase(temporary_db)
                before_ids = {int(row["id"]) for row in temporary_history.list_llm_runs()}
                count = interpret_week_with_openai(
                    temporary_db, year=args.anio, week=week,
                    model=model, reasoning_effort=effort,
                )
                run = next(
                    row for row in reversed(temporary_history.list_llm_runs())
                    if int(row["id"]) not in before_ids
                )
                findings = temporary_history.load_report_data(args.anio, week)["llm_findings"]
                result = {
                    "year": args.anio, "week": week, "model": model,
                    "reasoning_effort": effort, "finding_count": count,
                    "usage_and_cost": run, "findings": findings,
                }
                results.append(result)
                for index, finding in enumerate(findings, start=1):
                    review_rows.append({
                        "anio": args.anio, "semana": week, "modelo": model,
                        "nivel": effort, "hallazgo": index,
                        "tipo": finding["relation_type"],
                        "avisos": "|".join(finding["notice_numbers"]),
                        "correcto_0_o_1": "", "util_0_a_2": "",
                        "omitio_relacion_relevante_0_o_1": "",
                        "afirmacion_no_respaldada_0_o_1": "",
                        "comentario_revisor": "", "revisor": "", "fecha_revision": "",
                    })

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    result_path = output_dir / "resultados_api.json"
    result_path.write_text(
        json.dumps({"executed_at": timestamp, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    review_path = output_dir / "evaluacion_humana.csv"
    with review_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)
    total_cost = sum(float(row["usage_and_cost"]["total_cost_usd"]) for row in results)
    manifest = {
        "executed_at": timestamp,
        "database_sha256": sha256_file(database_path),
        "database_path_not_archived": str(database_path),
        "weeks": args.semanas,
        "configurations": [{"model": model, "reasoning_effort": effort} for model, effort in configurations],
        "calls_completed": len(results),
        "total_cost_usd": total_cost,
        "runtime": runtime_manifest(),
        "results_sha256": sha256_file(result_path),
        "review_status": "pending_human_review",
    }
    (output_dir / "MANIFIESTO.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"estado": "API_COMPLETA_REVISION_HUMANA_PENDIENTE", **manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
