from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT))

from agente_mantenimiento.llm_openai import FINDINGS_SCHEMA  # noqa: E402
from agente_mantenimiento.provenance import (  # noqa: E402
    runtime_manifest, sha256_file, sha256_json,
)


OFFICIAL_PATTERN = re.compile(r"^corrida_\d{4}-\d{2}-\d{2}_semana_\d{2}$")


def main() -> int:
    roots = [
        path for path in (PROJECT / "corridas").iterdir()
        if path.is_dir() and OFFICIAL_PATTERN.fullmatch(path.name)
    ]
    for root in sorted(roots):
        metadata_path = root / "METADATA.json"
        prompt_path = root / "prompts" / "SYSTEM_PROMPT.txt"
        context_path = root / "salida" / "contexto_llm.json"
        findings_path = root / "salida" / "hallazgos_llm.json"
        runs_path = root / "salida" / "ejecuciones_llm.json"
        required = (metadata_path, prompt_path, context_path, findings_path, runs_path)
        if not all(path.is_file() for path in required):
            raise FileNotFoundError(f"Corrida incompleta para auditoría: {root}")
        context = json.loads(context_path.read_text(encoding="utf-8"))
        findings = json.loads(findings_path.read_text(encoding="utf-8"))
        runs = json.loads(runs_path.read_text(encoding="utf-8")).get("runs", [])
        latest_run = runs[-1] if runs else {}
        original_artifacts = {
            str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name not in {"AUDITORIA_TRAZABILIDAD.json", "solicitud_llm.json"}
        }
        request_manifest = {
            "interface": "OpenAI Responses API",
            "method": "POST",
            "endpoint": "https://api.openai.com/v1/responses",
            "credential_source": "OPENAI_API_KEY environment variable (value not archived)",
            "store": False,
            "model": latest_run.get("model"),
            "reasoning_effort": latest_run.get("reasoning_effort"),
            "response_id": latest_run.get("response_id"),
            "system_prompt_sha256": sha256_file(prompt_path),
            "context_sha256": sha256_json(context),
            "structured_output_schema_sha256": sha256_json(FINDINGS_SCHEMA),
            "validated_output_sha256": sha256_json(findings),
            "post_validation": "agente_mantenimiento.llm_contract.validate_llm_payload",
            "reconstructed_from_archived_artifacts": True,
        }
        request_path = root / "salida" / "solicitud_llm.json"
        request_path.write_text(
            json.dumps(request_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        audit = {
            "audited_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "execution_source_reference": None,
            "execution_source_reference_status": "not_captured_contemporaneously",
            "statement": (
                "No se asignó retrospectivamente un commit. Los artefactos originales se autentican "
                "con hashes y la reproducción completa comienza en la versión 1.1.0."
            ),
            "audited_against_release": runtime_manifest(),
            "original_artifact_sha256": original_artifacts,
            "request_manifest_sha256": sha256_file(request_path),
        }
        (root / "AUDITORIA_TRAZABILIDAD.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps({"estado": "PASS", "corridas_auditadas": len(roots)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
