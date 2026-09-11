from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from agente_mantenimiento.provenance import runtime_manifest  # noqa: E402


OFFICIAL_PATTERN = re.compile(r"^corrida_\d{4}-\d{2}-\d{2}_semana_\d{2}$")
RUN_FILES = (
    "README.md", "METADATA.json", "entrada/ARCHIVOS.md",
    "prompts/SYSTEM_PROMPT.txt", "prompts/USER_PROMPT.txt",
    "salida/resultados.json", "salida/contexto_llm.json",
    "salida/hallazgos_llm.json", "salida/ejecuciones_llm.json",
    "salida/solicitud_llm.json", "validacion/VALIDACION.md",
    "AUDITORIA_TRAZABILIDAD.json",
)
ROOT_FILES = (
    "README.md", "DECISIONES.md", "HERRAMIENTAS_Y_CONECTORES.md",
    "REPRODUCIBILIDAD.md", "ARQUITECTURA_Y_EVOLUCION.md",
    "ANALISIS_ECONOMICO.md", "MATRIZ_CUMPLIMIENTO.md",
    "VERSION", "requirements-lock.txt",
)


def run_checked(arguments: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        arguments, cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    return {
        "command": " ".join(arguments),
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-4000:],
        "passed": completed.returncode == 0,
    }


def main() -> int:
    missing_root = [name for name in ROOT_FILES if not (PROJECT / name).is_file()]
    roots = sorted(
        path for path in (PROJECT / "corridas").iterdir()
        if path.is_dir() and OFFICIAL_PATTERN.fullmatch(path.name)
    )
    missing_run_files = {
        root.name: [name for name in RUN_FILES if not (root / name).is_file()]
        for root in roots
    }
    missing_run_files = {key: value for key, value in missing_run_files.items() if value}
    unit_tests = run_checked([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    reproduction = run_checked([sys.executable, "scripts/reproducir_demo.py"])
    checks = {
        "root_structure_complete": not missing_root,
        "eight_official_runs": len(roots) == 8,
        "official_run_evidence_complete": not missing_run_files,
        "unit_tests_passed": unit_tests["passed"],
        "safe_reproduction_passed": reproduction["passed"],
    }
    result = {
        "verified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing_root_files": missing_root,
        "official_run_count": len(roots),
        "missing_run_files": missing_run_files,
        "unit_tests": unit_tests,
        "reproduction": reproduction,
        "runtime": runtime_manifest(),
        "paid_model_comparison": "not_executed_by_this_verifier",
    }
    output = PROJECT / "pruebas" / "VERIFICACION_ENTREGA.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"estado": result["result"], "evidencia": str(output)}, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
