from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT / "pruebas" / "comparacion_modelos_real"
OFFICIAL_PATTERN = re.compile(r"^corrida_\d{4}-\d{2}-\d{2}_semana_(\d{2})$")


def context_for_week(week: int) -> dict[str, dict[str, object]]:
    root = next(
        path for path in (PROJECT / "corridas").iterdir()
        if path.is_dir() and OFFICIAL_PATTERN.fullmatch(path.name)
        and int(OFFICIAL_PATTERN.fullmatch(path.name).group(1)) == week
    )
    context = json.loads((root / "salida" / "contexto_llm.json").read_text(encoding="utf-8"))
    return {str(row["notice_number"]): row for row in context["failure_facts"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara el control objetivo y la revisión humana.")
    parser.add_argument("--directorio", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    results_dir = args.directorio.resolve()
    source = results_dir / "resultados_api.json"
    if not source.is_file():
        raise FileNotFoundError("Primero ejecutá scripts/comparar_modelos.py")
    payload = json.loads(source.read_text(encoding="utf-8"))
    contexts = {int(row["week"]): context_for_week(int(row["week"])) for row in payload["results"]}
    review_rows: list[dict[str, object]] = []
    summary: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {"calls": 0, "findings": 0, "scope_errors": 0, "cost_usd": 0.0, "tokens": 0}
    )
    for result in payload["results"]:
        week = int(result["week"])
        model = str(result["model"])
        effort = str(result["reasoning_effort"])
        key = (model, effort)
        summary[key]["calls"] += 1
        summary[key]["findings"] += int(result["finding_count"])
        summary[key]["cost_usd"] += float(result["usage_and_cost"]["total_cost_usd"])
        summary[key]["tokens"] += int(result["usage_and_cost"]["total_tokens"])
        context = contexts[week]
        for index, finding in enumerate(result["findings"], start=1):
            notice_numbers = [str(value) for value in finding["notice_numbers"]]
            facts = [context.get(notice) for notice in notice_numbers]
            unknown = [notice for notice, fact in zip(notice_numbers, facts) if fact is None]
            equipment = sorted({str(fact["equipment"]) for fact in facts if fact})
            relation_type = str(finding["relation_type"])
            scope_valid = (
                not unknown and (
                    (relation_type == "same_bridge" and len(equipment) == 1)
                    or (relation_type == "cross_bridge" and len(equipment) >= 2)
                )
            )
            if not scope_valid:
                summary[key]["scope_errors"] += 1
            fact_text = " || ".join(
                f"{notice}: {fact['equipment']} — {fact['description']} — causa: {fact['documented_cause']}"
                for notice, fact in zip(notice_numbers, facts) if fact
            )
            review_rows.append({
                "anio": result["year"], "semana": week, "modelo": model,
                "nivel": effort, "hallazgo": index, "tipo": relation_type,
                "avisos": "|".join(notice_numbers), "puentes": "|".join(equipment),
                "alcance_valido_python": 1 if scope_valid else 0,
                "avisos_desconocidos": "|".join(unknown),
                "titulo": finding["title"], "fundamento_llm": finding["rationale"],
                "hechos_fuente": fact_text,
                "correcto_0_o_1": "", "util_0_a_2": "",
                "afirmacion_no_respaldada_0_o_1": "",
                "comentario_revisor": "", "rol_revisor": "", "fecha_revision": "",
            })
    review_path = results_dir / "revision_tecnica.csv"
    with review_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)
    summary_rows = []
    for (model, effort), values in summary.items():
        summary_rows.append({"model": model, "reasoning_effort": effort, **values})
    eligible = {
        (str(row["model"]), str(row["reasoning_effort"]))
        for row in summary_rows if int(row["scope_errors"]) == 0 and int(row["calls"]) == 2
    }
    eligible_rows = [
        row for row in review_rows if (str(row["modelo"]), str(row["nivel"])) in eligible
    ]
    eligible_path = results_dir / "revision_candidatos_validos.csv"
    with eligible_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(eligible_rows[0]))
        writer.writeheader()
        writer.writerows(eligible_rows)
    objective = {
        "source": "resultados_api.json",
        "checks": {
            "calls_expected": 6,
            "calls_observed": len(payload["results"]),
            "all_outputs_passed_original_json_validation": True,
            "all_notice_numbers_exist": all(not row["avisos_desconocidos"] for row in review_rows),
            "relation_scope_errors_found": sum(int(row["alcance_valido_python"] == 0) for row in review_rows),
        },
        "configurations": summary_rows,
        "configurations_eligible_for_human_review": [
            {"model": model, "reasoning_effort": effort} for model, effort in sorted(eligible)
        ],
        "human_review_status": "pending",
        "note": (
            "La validez estructural no demuestra corrección técnica. Las columnas humanas "
            "de revision_tecnica.csv deben completarse por el responsable."
        ),
    }
    (results_dir / "RESUMEN_OBJETIVO.json").write_text(
        json.dumps(objective, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(objective, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
