from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT / "pruebas" / "comparacion_modelos_real"
COMPACT_REVIEW = re.compile(
    r"^([01])-([012])-([01])(?:\s+comentario_revisor:\s*(.*))?$", re.IGNORECASE
)


def integer(row: dict[str, str], field: str, allowed: set[int]) -> int:
    try:
        value = int(row[field])
    except (KeyError, ValueError) as error:
        raise ValueError(f"Falta completar {field} en {row.get('modelo')} S{row.get('semana')} hallazgo {row.get('hallazgo')}") from error
    if value not in allowed:
        raise ValueError(f"{field} debe ser uno de {sorted(allowed)}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Cierra el benchmark después de la revisión humana.")
    parser.add_argument("--directorio", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--revision", type=Path,
    )
    parser.add_argument("--rol-revisor", required=True)
    parser.add_argument("--fecha", default=date.today().isoformat())
    args = parser.parse_args()
    results_dir = args.directorio.resolve()
    revision_path = args.revision or (results_dir / "revision_candidatos_validos.csv")
    rows = list(csv.DictReader(revision_path.open(encoding="utf-8-sig", newline="")))
    if not rows:
        raise ValueError("La planilla de revisión no contiene hallazgos.")
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not row.get("correcto_0_o_1", "").strip():
            compact = COMPACT_REVIEW.fullmatch(row.get("fecha_revision", "").strip())
            if compact:
                row["correcto_0_o_1"] = compact.group(1)
                row["util_0_a_2"] = compact.group(2)
                row["afirmacion_no_respaldada_0_o_1"] = compact.group(3)
                if compact.group(4) and not row.get("comentario_revisor", "").strip():
                    row["comentario_revisor"] = compact.group(4).strip()
                row["fecha_revision"] = args.fecha
        row["rol_revisor"] = args.rol_revisor
        if not row.get("fecha_revision", "").strip():
            row["fecha_revision"] = args.fecha
        grouped[(row["modelo"], row["nivel"])].append(row)
    normalized_path = results_dir / "revision_humana_normalizada.csv"
    with normalized_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    objective = json.loads((results_dir / "RESUMEN_OBJETIVO.json").read_text(encoding="utf-8"))
    costs = {
        (row["model"], row["reasoning_effort"]): float(row["cost_usd"])
        for row in objective["configurations"]
    }
    evaluations = []
    for (model, effort), findings in grouped.items():
        correct = [integer(row, "correcto_0_o_1", {0, 1}) for row in findings]
        utility = [integer(row, "util_0_a_2", {0, 1, 2}) for row in findings]
        unsupported = [integer(row, "afirmacion_no_respaldada_0_o_1", {0, 1}) for row in findings]
        correctness = sum(correct) / len(correct)
        average_utility = sum(utility) / len(utility)
        passed = correctness >= 0.80 and average_utility >= 1.5 and sum(unsupported) == 0
        evaluations.append({
            "model": model, "reasoning_effort": effort, "findings_reviewed": len(findings),
            "correctness_rate": correctness, "average_utility_0_to_2": average_utility,
            "unsupported_claims": sum(unsupported), "cost_two_calls_usd": costs[(model, effort)],
            "passed": passed,
        })
    passing = sorted(
        (row for row in evaluations if row["passed"]), key=lambda row: row["cost_two_calls_usd"]
    )
    selected = passing[0] if passing else None
    conclusion = {
        "reviewed_by_role": args.rol_revisor,
        "review_date": args.fecha,
        "evaluations": evaluations,
        "selected_configuration": selected,
        "status": "complete" if selected else "no_configuration_passed",
    }
    (results_dir / "CONCLUSION_EVALUACION.json").write_text(
        json.dumps(conclusion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(conclusion, ensure_ascii=False, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
