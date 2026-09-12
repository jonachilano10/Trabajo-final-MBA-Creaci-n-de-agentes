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
from agente_mantenimiento.economics import calculate_cost  # noqa: E402
from agente_mantenimiento.llm_contract import LLMFindingValidationError  # noqa: E402
from agente_mantenimiento.llm_openai import LLMServiceError, interpret_week_with_openai  # noqa: E402
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


def usage_evidence(error: LLMFindingValidationError, model: str) -> dict[str, object]:
    usage = getattr(error, "api_usage", {}) or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    cached_tokens = int(input_details.get("cached_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return {
        "model": model,
        "response_id": getattr(error, "api_response_id", ""),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or input_tokens + output_tokens),
        **calculate_cost(
            model, input_tokens=input_tokens, cached_input_tokens=cached_tokens,
            output_tokens=output_tokens,
        ),
    }


def save_checkpoint(path: Path, executed_at: str, results: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"executed_at": executed_at, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        parser.error("Falta OPENAI_API_KEY en el entorno.")
    if api_key.lower() in {"tu_clave", "your_key", "your_api_key"} or len(api_key) < 20:
        parser.error(
            "OPENAI_API_KEY contiene un ejemplo o una clave incompleta. "
            "Reemplazala por la clave real sin publicarla ni guardarla en el proyecto."
        )
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
    result_path = output_dir / "resultados_api.json"
    executed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    results: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    failed_configurations: set[tuple[str, str]] = set()
    for week in args.semanas:
        for model, effort in configurations:
            if (model, effort) in failed_configurations:
                continue
            print(f"Iniciando S{week} — {model} — {effort}...", flush=True)
            with tempfile.TemporaryDirectory(prefix="comparacion_llm_") as temporary:
                temporary_db = Path(temporary) / "comparacion.sqlite3"
                shutil.copy2(database_path, temporary_db)
                temporary_history = HistoryDatabase(temporary_db)
                before_ids = {int(row["id"]) for row in temporary_history.list_llm_runs()}
                try:
                    count = interpret_week_with_openai(
                        temporary_db, year=args.anio, week=week,
                        model=model, reasoning_effort=effort,
                    )
                except LLMFindingValidationError as error:
                    invalid_findings = getattr(error, "invalid_payload", {}).get("findings", [])
                    result = {
                        "status": "validation_failed",
                        "year": args.anio, "week": week, "model": model,
                        "reasoning_effort": effort, "finding_count": len(invalid_findings),
                        "validation_error": str(error),
                        "usage_and_cost": usage_evidence(error, model),
                        "findings": invalid_findings,
                    }
                    results.append(result)
                    failed_configurations.add((model, effort))
                    save_checkpoint(result_path, executed_at, results)
                    print(f"RECHAZADO S{week} — {model}: {error}", flush=True)
                    continue
                except LLMServiceError as error:
                    print(
                        f"ERROR API en semana {week}, modelo {model}, nivel {effort}: {error}",
                        file=__import__("sys").stderr,
                    )
                    save_checkpoint(result_path, executed_at, results)
                    return 1
                run = next(
                    row for row in reversed(temporary_history.list_llm_runs())
                    if int(row["id"]) not in before_ids
                )
                findings = temporary_history.load_report_data(args.anio, week)["llm_findings"]
                result = {
                    "status": "completed",
                    "year": args.anio, "week": week, "model": model,
                    "reasoning_effort": effort, "finding_count": count,
                    "usage_and_cost": run, "findings": findings,
                }
                results.append(result)
                save_checkpoint(result_path, executed_at, results)
                print(f"COMPLETO S{week} — {model}: {count} hallazgos", flush=True)
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
    review_path = output_dir / "evaluacion_humana.csv"
    if review_rows:
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
        "calls_attempted": len(results),
        "calls_completed": sum(row["status"] == "completed" for row in results),
        "validation_failures": sum(row["status"] == "validation_failed" for row in results),
        "skipped_after_failure": len(args.semanas) * len(configurations) - len(results),
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
