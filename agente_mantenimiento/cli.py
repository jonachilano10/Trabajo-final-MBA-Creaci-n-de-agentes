from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .analysis import InputValidationError, analyze_week
from .config import DEFAULT_DB_PATH, DEFAULT_OUTPUT_DIR
from .database import DuplicateWeekError, HistoryDatabase
from .llm_contract import LLMFindingValidationError, export_llm_context, import_llm_findings
from .llm_openai import LLMServiceError, interpret_week_with_openai
from .report import generate_report
from .privacy import ConfidentialDataError, validate_no_confidential_data


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Usá el formato AAAA-MM-DD.") from error


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Agente local de disponibilidad e historial.")
    root.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Ruta de la base SQLite.")
    commands = root.add_subparsers(dest="command", required=True)

    process = commands.add_parser("procesar", help="Validar, calcular, guardar y generar el reporte.")
    process.add_argument("--anio", type=int, required=True)
    process.add_argument("--semana", type=int, required=True)
    process.add_argument("--desde", type=iso_date, required=True)
    process.add_argument("--hasta", type=iso_date, required=True)
    process.add_argument("--avisos", type=Path, required=True)
    process.add_argument("--notificaciones", type=Path, required=True)
    process.add_argument("--mantenimiento", type=Path, required=True)
    process.add_argument("--salida", type=Path)

    report = commands.add_parser("reporte", help="Regenerar el reporte de una semana guardada.")
    report.add_argument("--anio", type=int, required=True)
    report.add_argument("--semana", type=int, required=True)
    report.add_argument("--salida", type=Path)

    commands.add_parser("historial", help="Listar las semanas almacenadas.")
    llm_export = commands.add_parser("exportar-llm", help="Exportar hechos textuales para interpretación.")
    llm_export.add_argument("--salida", type=Path, required=True)
    llm_export.add_argument("--anio", type=int)
    llm_export.add_argument("--semana", type=int)
    llm_import = commands.add_parser("importar-llm", help="Validar e importar hallazgos narrativos.")
    llm_import.add_argument("--entrada", type=Path, required=True)
    llm_import.add_argument("--anio", type=int)
    llm_import.add_argument("--semana", type=int)
    interpret = commands.add_parser("interpretar", help="Generar la interpretación con OpenAI y regenerar el reporte.")
    interpret.add_argument("--anio", type=int, required=True)
    interpret.add_argument("--semana", type=int, required=True)
    interpret.add_argument("--salida", type=Path)
    return root


def default_report_path(year: int, week: int) -> Path:
    return DEFAULT_OUTPUT_DIR / f"semana_{year}_{week:02d}" / "reporte.html"


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    database = HistoryDatabase(args.db)
    try:
        if args.command == "procesar":
            if not 1 <= args.semana <= 53:
                raise InputValidationError("La semana debe estar entre 1 y 53.")
            if database.week_exists(args.anio, args.semana):
                raise DuplicateWeekError(
                    f"La semana {args.semana}/{args.anio} ya está cargada. No se realizaron cambios."
                )
            validate_no_confidential_data((path, path.name) for path in (
                args.avisos, args.notificaciones, args.mantenimiento
            ))
            analysis = analyze_week(
                year=args.anio, week=args.semana, start_date=args.desde, end_date=args.hasta,
                notices_path=args.avisos, notifications_path=args.notificaciones,
                maintenance_path=args.mantenimiento,
            )
            database.save_analysis(analysis)
            output = generate_report(
                args.db, year=args.anio, week=args.semana,
                output_path=args.salida or default_report_path(args.anio, args.semana),
            )
            print(json.dumps({
                "estado": "ok", "semana": args.semana, "anio": args.anio,
                "disponibilidad": analysis["global"]["availability"],
                "horas_parada": analysis["global"]["stop_hours"],
                "detenciones": analysis["global"]["stoppage_count"],
                "interpretacion_llm": "pendiente_hasta_exportar_e_importar_hallazgos",
                "reporte": str(output), "base": str(Path(args.db).resolve()),
            }, ensure_ascii=False, indent=2))
        elif args.command == "reporte":
            output = generate_report(
                args.db, year=args.anio, week=args.semana,
                output_path=args.salida or default_report_path(args.anio, args.semana),
            )
            print(f"Reporte generado: {output}")
        elif args.command == "historial":
            weeks = database.list_weeks()
            if not weeks:
                print("La base está vacía: todavía no existe historial suficiente.")
            for row in weeks:
                print(
                    f"S{row['week']}/{row['year']} | {row['start_date']} a {row['end_date']} | "
                    f"disponibilidad {row['global_availability']:.2f}% | "
                    f"parada {row['global_stop_hours']:.2f} h | {row['global_stoppage_count']} detenciones"
                )
        elif args.command == "exportar-llm":
            print(f"Contexto exportado: {export_llm_context(args.db, args.salida, year=args.anio, week=args.semana)}")
        elif args.command == "importar-llm":
            print(f"Hallazgos importados: {import_llm_findings(args.db, args.entrada, year=args.anio, week=args.semana)}")
        elif args.command == "interpretar":
            count = interpret_week_with_openai(args.db, year=args.anio, week=args.semana)
            output = generate_report(
                args.db, year=args.anio, week=args.semana,
                output_path=args.salida or default_report_path(args.anio, args.semana),
            )
            print(f"Interpretación completada: {count} hallazgos preliminares. Reporte: {output}")
        return 0
    except DuplicateWeekError as error:
        print(f"DUPLICADO: {error}", file=sys.stderr)
        return 2
    except (InputValidationError, ConfidentialDataError, LLMFindingValidationError, LLMServiceError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
