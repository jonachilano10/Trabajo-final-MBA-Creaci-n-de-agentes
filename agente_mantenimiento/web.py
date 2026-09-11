from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import html
import json
import os
import shutil
import tempfile
import time
import secrets
from datetime import date, datetime
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .analysis import InputValidationError, analyze_week
from .config import DEFAULT_ARCHIVE_DIR, DEFAULT_DB_PATH, DEFAULT_OUTPUT_DIR, PROJECT_DIR
from .database import DuplicateWeekError, HistoryDatabase
from .economics import MODEL_PRICES, comparison_rows, estimate_text_tokens
from .llm_contract import build_llm_context
from .llm_openai import (
    FINDINGS_SCHEMA, INSTRUCTIONS, LLMServiceError, SYSTEM_PROMPT_PATH,
    interpret_week_with_openai,
)
from .provenance import runtime_manifest, sha256_file, sha256_json
from .report import generate_report
from .privacy import ConfidentialDataError, validate_no_confidential_data


MAX_REQUEST_BYTES = 80 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5
_LOGIN_FAILURES: dict[str, list[float]] = {}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def report_path(year: int, week: int) -> Path:
    return DEFAULT_OUTPUT_DIR / f"semana_{year}_{week:02d}" / "reporte.html"


def archive_path(year: int, week: int) -> Path:
    return DEFAULT_ARCHIVE_DIR / f"corrida_{date.today().isoformat()}_semana_{week:02d}"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _make_session(secret: str) -> tuple[str, str]:
    csrf = secrets.token_urlsafe(24)
    payload = f"{int(time.time()) + SESSION_SECONDS}|{csrf}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}", csrf


def _read_session(token: str, secret: str) -> str | None:
    try:
        encoded, signed = token.split(".", 1)
        payload = _b64decode(encoded)
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(signed)):
            return None
        expiry, csrf = payload.decode("utf-8").split("|", 1)
        return csrf if int(expiry) >= int(time.time()) else None
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def login_page(message: str = "") -> str:
    alert = f"<div class='alert'>{esc(message)}</div>" if message else ""
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>Ingreso al agente</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#edf2f5;color:#1c2a35;font:15px Arial,sans-serif;display:grid;min-height:100vh;place-items:center}}main{{width:min(430px,calc(100% - 32px));background:white;border:1px solid #d7e0e7;border-radius:10px;padding:28px;box-shadow:0 6px 24px #17324d22}}h1{{font-size:23px;color:#17324d;margin:0 0 8px}}p{{color:#63727e}}label{{font-weight:700;color:#17324d}}input{{width:100%;padding:12px;margin:8px 0 18px;border:1px solid #aebbc5;border-radius:5px}}button{{width:100%;border:0;border-radius:5px;background:#28658f;color:white;padding:12px;font-weight:700}}.alert{{background:#fdecec;color:#9d2c2c;padding:11px;margin-bottom:15px;border-radius:5px}}</style></head>
<body><main><h1>Agente de disponibilidad</h1><p>Ingresá la contraseña autorizada para acceder.</p>{alert}<form method='post' action='/login'><label>Contraseña<input name='password' type='password' autocomplete='current-password' required autofocus></label><button type='submit'>Ingresar</button></form></main></body></html>"""


def _history_rows(database: HistoryDatabase, csrf: str) -> str:
    weeks = list(reversed(database.list_weeks()))
    if not weeks:
        return "<tr><td colspan='6'>Todavía no hay semanas cargadas.</td></tr>"
    rows = []
    with database.connect() as connection:
        counts = {
            (row["report_year"], row["report_week"]): row["total"]
            for row in connection.execute(
                "SELECT report_year, report_week, count(1) total FROM llm_findings GROUP BY report_year, report_week"
            )
        }
    for row in weeks:
        count = counts.get((row["year"], row["week"]), 0)
        status = (
            f"Completa: {count} interpretaciones preliminares"
            if count
            else "Incompleta: interpretación LLM pendiente"
        )
        retry = "" if count else (
            f"<form class='inline' method='post' action='/interpretar'>"
            f"<input type='hidden' name='csrf' value='{esc(csrf)}'>"
            f"<input type='hidden' name='year' value='{row['year']}'>"
            f"<input type='hidden' name='week' value='{row['week']}'>"
            "<button class='small secondary' type='submit'>Reintentar LLM</button></form>"
        )
        rows.append(
            f"<tr><td>S{row['week']}/{row['year']}</td><td>{row['start_date']} a {row['end_date']}</td>"
            f"<td class='num'>{row['global_availability']:.2f} %</td>"
            f"<td class='num'>{row['global_stop_hours']:.2f} h</td>"
            f"<td>{esc(status)}</td><td><a class='button small' target='_blank' "
            f"href='/reporte?year={row['year']}&week={row['week']}'>Abrir reporte</a>{retry}</td></tr>"
        )
    return "".join(rows)


def _economic_panel(database: HistoryDatabase, csrf: str) -> str:
    weeks = database.list_weeks()
    input_tokens = 0
    context_label = "Sin semanas cargadas"
    if weeks:
        latest = weeks[-1]
        context = build_llm_context(database.path, year=latest["year"], week=latest["week"])
        input_tokens = estimate_text_tokens({
            "instructions": INSTRUCTIONS,
            "input": context,
            "structured_output_schema": FINDINGS_SCHEMA,
        })
        context_label = f"S{latest['week']}/{latest['year']}"
    assumed_output = 2_000
    rows = comparison_rows(input_tokens, assumed_output) if input_tokens else []
    estimates = "".join(
        f"<tr><td>{esc(row['label'])}</td><td class='num'>{input_tokens:,}</td>"
        f"<td class='num'>{assumed_output:,}</td><td class='num'>US$ {row['estimated_cost_usd']:.4f}</td>"
        f"<td class='num'>{row['savings_vs_gpt54_percent']:.1f} %</td></tr>"
        for row in rows[::5]
    ) or "<tr><td colspan='5'>Cargá la primera semana para estimar el contexto.</td></tr>"
    runs = database.list_llm_runs()
    actual = "".join(
        f"<tr><td>S{r['report_week']}/{r['report_year']}</td><td>{esc(r['model'])}</td>"
        f"<td>{esc(r['reasoning_effort'])}</td><td class='num'>{r['input_tokens']:,}</td>"
        f"<td class='num'>{r['output_tokens']:,}</td><td class='num'>{r['reasoning_tokens']:,}</td>"
        f"<td class='num'>US$ {r['total_cost_usd']:.6f}</td></tr>" for r in runs
    ) or "<tr><td colspan='7'>Todavía no hay consumo real medido por la API.</td></tr>"
    total = sum(r["total_cost_usd"] for r in runs)
    week_options = "".join(
        f"<option value='{w['year']}:{w['week']}'>S{w['week']}/{w['year']}</option>" for w in reversed(weeks)
    )
    model_options = "".join(
        f"<option value='{model}'>{esc(price.label)}</option>" for model, price in MODEL_PRICES.items()
    )
    benchmark = ""
    if weeks:
        benchmark = f"""<form class='grid' method='post' action='/interpretar' onsubmit='return prepareBenchmark(this)'>
<input type='hidden' name='csrf' value='{esc(csrf)}'>
<label>Semana a comparar<select name='period'>{week_options}</select></label>
<label>Modelo<select name='model'>{model_options}</select></label>
<label>Nivel<select name='reasoning_effort'><option>none</option><option>low</option><option selected>medium</option><option>high</option><option>xhigh</option></select></label>
<input type='hidden' name='year'><input type='hidden' name='week'>
<label>Prueba paga<button type='submit' style='margin-top:6px;width:100%'>Ejecutar y medir</button></label></form>
<p class='hint'>Cada clic realiza una llamada real a la API y puede generar cargos. Permite repetir una semana con distintas combinaciones sin duplicar sus datos técnicos.</p>"""
    return f"""<section class='card'><h2>Análisis económico del LLM</h2>
<p>Estimación para <strong>{context_label}</strong>: aproximadamente <strong>{input_tokens:,} tokens de entrada</strong> y un supuesto común de <strong>{assumed_output:,} tokens de salida</strong>.</p>
<div class='table-wrap'><table><thead><tr><th>Modelo</th><th class='num'>Entrada estimada</th><th class='num'>Salida supuesta</th><th class='num'>Costo estimado/corrida</th><th class='num'>Ahorro vs GPT-5.4</th></tr></thead><tbody>{estimates}</tbody></table></div>
<p class='hint'>Los niveles none, low, medium, high y xhigh tienen la misma tarifa por token. Un nivel mayor puede consumir más tokens de razonamiento; ese consumo no se inventa antes de ejecutar.</p>
<div class='table-wrap'><table><thead><tr><th>Semana</th><th>Modelo</th><th>Razonamiento</th><th class='num'>Entrada</th><th class='num'>Salida total</th><th class='num'>Razonamiento</th><th class='num'>Costo real</th></tr></thead><tbody>{actual}</tbody></table></div>
<p><strong>Gasto real acumulado registrado: US$ {total:.6f}</strong></p>{benchmark}</section>"""


def page(database: HistoryDatabase, *, csrf: str, message: str = "", error: bool = False) -> str:
    key_ready = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    banner = ""
    if message:
        banner = f"<div class='alert {'error' if error else 'success'}'>{esc(message)}</div>"
    llm_state = (
        "Interpretación automática habilitada"
        if key_ready else "Falta OPENAI_API_KEY: el cálculo funciona, pero la corrida quedará incompleta"
    )
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>Agente de disponibilidad</title>
<style>
:root{{--navy:#17324d;--blue:#28658f;--soft:#f3f6f8;--line:#d7e0e7;--ink:#1c2a35;--muted:#63727e;--ok:#1e6b45;--bad:#9d2c2c}}
*{{box-sizing:border-box}}body{{margin:0;background:#edf2f5;color:var(--ink);font:15px/1.45 Arial,sans-serif}}
header{{background:var(--navy);color:#fff;padding:28px max(24px,calc((100% - 1180px)/2))}}header h1{{margin:0 0 6px;font-size:27px}}header p{{margin:0;color:#d8e5ee}}
main{{max-width:1180px;margin:auto;padding:28px 24px 50px}}.card{{background:#fff;border:1px solid var(--line);border-radius:9px;padding:22px;margin-bottom:22px;box-shadow:0 2px 7px #18334d0d}}
h2{{margin:0 0 16px;color:var(--navy);font-size:20px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.files{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}}
.grid>*,.files>*{{min-width:0}}label{{display:block;font-weight:700;color:var(--navy);font-size:13px}}input,select{{width:100%;min-width:0;margin-top:6px;padding:10px;border:1px solid #aebbc5;border-radius:5px;background:#fff}}input[type=file]{{padding:9px;background:var(--soft);max-width:100%}}
.hint{{color:var(--muted);font-size:12px;margin-top:8px}}button,.button{{border:0;border-radius:5px;background:var(--blue);color:#fff;padding:11px 17px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}}button:hover,.button:hover{{filter:brightness(.94)}}.secondary{{background:#647987}}.small{{padding:7px 10px;font-size:12px;margin-left:6px}}.actions{{margin-top:18px;display:flex;align-items:center;gap:12px}}.inline{{display:inline}}
.status{{padding:10px 12px;border-left:4px solid {'var(--ok)' if key_ready else '#b66a00'};background:var(--soft);margin-bottom:18px}}.alert{{padding:13px 15px;border-radius:5px;margin-bottom:18px}}.success{{background:#e8f5ee;color:var(--ok)}}.error{{background:#fdecec;color:var(--bad)}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:6px}}table{{width:100%;border-collapse:collapse;min-width:850px}}th{{text-align:left;background:var(--soft);color:var(--navy);font-size:12px;padding:10px}}td{{padding:10px;border-top:1px solid #e7ecef;vertical-align:middle}}.num{{text-align:right;white-space:nowrap}}
#working{{display:none;color:var(--navy);font-weight:700}}@media(max-width:850px){{.grid,.files{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{.grid,.files{{grid-template-columns:1fr}}}}
</style></head><body><header><h1>Agente de disponibilidad de puentes grúa</h1><p>Cargá los tres Excel de una semana. Python valida y calcula; el LLM interpreta las fallas de forma preliminar.</p><form method='post' action='/logout' style='margin-top:12px'><input type='hidden' name='csrf' value='{esc(csrf)}'><button class='small secondary' type='submit'>Cerrar sesión</button></form></header><main>
{banner}<section class='card'><h2>Nueva semana</h2><div class='status'>{esc(llm_state)}</div>
<form id='upload-form' method='post' action='/procesar' enctype='multipart/form-data'>
<input type='hidden' name='csrf' value='{esc(csrf)}'>
<div class='grid'><label>Año<input id='year' name='year' type='number' min='2000' max='2100' value='2026' required></label>
<label>Semana<input id='week' name='week' type='number' min='1' max='53' required></label>
<label>Desde<input id='start_date' name='start_date' type='date' required></label>
<label>Hasta<input id='end_date' name='end_date' type='date' required></label></div>
<div class='grid' style='margin-top:14px'><label>Modelo LLM<select name='model'>{''.join(f"<option value='{m}'{' selected' if m == 'gpt-5.4-mini' else ''}>{esc(p.label)}</option>" for m, p in MODEL_PRICES.items())}</select></label>
<label>Nivel de razonamiento<select name='reasoning_effort'><option>none</option><option>low</option><option selected>medium</option><option>high</option><option>xhigh</option></select></label></div>
<div class='files'><label>Excel de avisos<input name='notices' type='file' accept='.xlsx,.xlsm' required></label>
<label>Excel de notificaciones<input name='notifications' type='file' accept='.xlsx,.xlsm' required></label>
<label>Excel de tareas en sala<input name='maintenance' type='file' accept='.xlsx,.xlsm' required></label></div>
<p class='hint'>Los archivos se usan temporalmente y no se modifican. Sólo se guardan resultados estructurados, nombres y huellas SHA-256.</p>
<div class='actions'><button type='submit'>Validar y analizar</button><span id='working'>Procesando… no cierres esta página.</span></div></form></section>
<section class='card'><h2>Historial almacenado</h2><div class='table-wrap'><table><thead><tr><th>Semana</th><th>Período</th><th class='num'>Disponibilidad</th><th class='num'>Parada</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{_history_rows(database, csrf)}</tbody></table></div></section>
{_economic_panel(database, csrf)}
</main><script>
function dates(){{const y=+document.querySelector('#year').value,w=+document.querySelector('#week').value;if(!y||!w)return;const jan4=new Date(Date.UTC(y,0,4)),day=jan4.getUTCDay()||7,monday=new Date(jan4);monday.setUTCDate(jan4.getUTCDate()-day+1+(w-1)*7);const end=new Date(monday);end.setUTCDate(monday.getUTCDate()+6);document.querySelector('#start_date').value=monday.toISOString().slice(0,10);document.querySelector('#end_date').value=end.toISOString().slice(0,10)}}
function prepareBenchmark(form){{const parts=form.period.value.split(':');form.year.value=parts[0];form.week.value=parts[1];return confirm('Esta prueba usa la API y puede generar cargos. ¿Continuar?')}}
document.querySelector('#week').addEventListener('change',dates);document.querySelector('#year').addEventListener('change',dates);document.querySelector('#upload-form').addEventListener('submit',()=>{{document.querySelector('#working').style.display='inline'}});
</script></body></html>"""


def _parse_multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0 or length > MAX_REQUEST_BYTES:
        raise InputValidationError("La carga está vacía o supera el límite total de 80 MB.")
    content_type = handler.headers.get("Content-Type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise InputValidationError("El formulario no contiene una carga de archivos válida.")
    raw = handler.rfile.read(length)
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii") + raw
    )
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[str(name)] = (Path(filename).name, payload)
        elif name:
            fields[str(name)] = payload.decode(part.get_content_charset() or "utf-8").strip()
    return fields, files


def _write_llm_evidence(root: Path, database_path: Path, year: int, week: int) -> None:
    database = HistoryDatabase(database_path)
    context = build_llm_context(database_path, year=year, week=week)
    report_data = database.load_report_data(year, week)
    finding_fields = (
        "relation_type", "title", "notice_numbers", "confidence", "rationale", "human_review"
    )
    findings = [
        {field: row[field] for field in finding_fields}
        for row in report_data.get("llm_findings", [])
    ]
    runs = [
        row for row in database.list_llm_runs()
        if int(row["report_year"]) == year and int(row["report_week"]) == week
    ]
    (root / "salida" / "contexto_llm.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "salida" / "hallazgos_llm.json").write_text(
        json.dumps({"findings": findings}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "salida" / "ejecuciones_llm.json").write_text(
        json.dumps({"runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    latest_run = runs[-1] if runs else {}
    request_manifest = {
        "interface": "OpenAI Responses API",
        "method": "POST",
        "endpoint": "https://api.openai.com/v1/responses",
        "credential_source": "OPENAI_API_KEY environment variable (value never archived)",
        "store": False,
        "model": latest_run.get("model"),
        "reasoning_effort": latest_run.get("reasoning_effort"),
        "response_id": latest_run.get("response_id"),
        "system_prompt_sha256": sha256_file(SYSTEM_PROMPT_PATH),
        "context_sha256": sha256_json(context),
        "structured_output_schema_sha256": sha256_json(FINDINGS_SCHEMA),
        "validated_output_sha256": sha256_json({"findings": findings}),
        "post_validation": "agente_mantenimiento.llm_contract.validate_llm_payload",
    }
    (root / "salida" / "solicitud_llm.json").write_text(
        json.dumps(request_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata_path = root / "METADATA.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        previous_status = metadata.get("llm_status", "pending")
        current_status = "completed" if findings else "pending"
        metadata["llm_status"] = current_status
        metadata["llm_error"] = None if findings else metadata.get("llm_error")
        metadata["llm_evidence_updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        readme_path = root / "README.md"
        if readme_path.exists() and previous_status != current_status:
            content = readme_path.read_text(encoding="utf-8").replace(
                f"- Estado LLM: `{previous_status}`.", f"- Estado LLM: `{current_status}`."
            )
            readme_path.write_text(content, encoding="utf-8")


def _save_archive(
    analysis: dict,
    year: int,
    week: int,
    report: Path,
    *,
    database_path: Path,
    requested_model: str,
    requested_effort: str,
    llm_error: str | None,
    execution_entrypoint: str = "web:POST /procesar",
) -> None:
    root = archive_path(year, week)
    (root / "entrada").mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "salida").mkdir(parents=True, exist_ok=True)
    (root / "validacion").mkdir(parents=True, exist_ok=True)
    (root / "salida" / "resultados.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sources = analysis["sources"]
    manifest = "# Manifiesto de entradas\n\nLos Excel se utilizaron temporalmente y no fueron modificados.\n\n"
    for key in ("notices", "notifications", "maintenance"):
        manifest += f"- `{sources[key]['name']}` — SHA-256 `{sources[key]['sha256']}`\n"
    (root / "entrada" / "ARCHIVOS.md").write_text(manifest, encoding="utf-8")
    user_prompt = (
        f"Objetivo: calcular la disponibilidad de la semana {week}, comprendida del "
        f"{analysis['period']['start_date']} al {analysis['period']['end_date']}.\n\n"
        "Información: se adjuntan los archivos de avisos, solicitudes de tareas en sala "
        "y notificaciones.\n\n"
        "- No calcular ni estimar proyecciones del mes ni de otras semanas.\n"
        "- Recalcular usando exclusivamente los archivos cargados.\n"
        "- Conservar la interpretación del LLM como preliminar y sujeta a revisión humana.\n\n"
        "Archivos utilizados:\n"
        f"- Avisos: {sources['notices']['name']}\n"
        f"- Notificaciones: {sources['notifications']['name']}\n"
        f"- Tareas en sala: {sources['maintenance']['name']}\n"
    )
    (root / "prompts" / "USER_PROMPT.txt").write_text(user_prompt, encoding="utf-8")
    canonical_prompt = PROJECT_DIR / "prompts" / "system_prompt.md"
    if canonical_prompt.exists():
        shutil.copy2(canonical_prompt, root / "prompts" / "SYSTEM_PROMPT.txt")
    for source, destination in (
        (PROJECT_DIR / "prompts" / "user_prompt.md", root / "prompts" / "USER_PROMPT_TEMPLATE.md"),
        (
            PROJECT_DIR / "prompts" / "contrato_funcional_agente.md",
            root / "prompts" / "CONTRATO_FUNCIONAL_AGENTE.md",
        ),
    ):
        if source.exists():
            shutil.copy2(source, destination)
    issues = analysis["validation_issues"]
    validation = "# Validación\n\n" + ("No se detectaron observaciones.\n" if not issues else "\n".join(
        f"- {row.get('severity', 'warning')}: {row['type']} — {row.get('detail', '')}" for row in issues
    ))
    (root / "validacion" / "VALIDACION.md").write_text(validation, encoding="utf-8")
    shutil.copy2(report, root / "salida" / f"Reporte_Disponibilidad_Semana{week}.html")
    _write_llm_evidence(root, database_path, year, week)
    metadata = {
        "archived_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "year": year,
        "week": week,
        "period": analysis["period"],
        "requested_model": requested_model,
        "requested_reasoning_effort": requested_effort,
        "llm_status": "completed" if llm_error is None else "pending",
        "llm_error": llm_error,
        "source_sha256": {key: sources[key]["sha256"] for key in sources},
        "execution": {
            "entrypoint": execution_entrypoint,
            "database_mode": "SQLite local; archivos fuente procesados temporalmente",
        },
        "runtime": runtime_manifest(),
        "artifact_sha256": {
            str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
            for path in sorted(root.rglob("*")) if path.is_file() and path.name != "METADATA.json"
        },
    }
    (root / "METADATA.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    readme = (
        f"# Corrida {week}/{year}\n\n"
        f"- Período: {analysis['period']['start_date']} al {analysis['period']['end_date']}.\n"
        f"- Archivada: {metadata['archived_at']}.\n"
        f"- Modelo solicitado: `{requested_model}`.\n"
        f"- Nivel de razonamiento: `{requested_effort}`.\n"
        f"- Estado LLM: `{metadata['llm_status']}`.\n"
        "- Los cálculos fueron realizados por Python y la interpretación requiere revisión humana.\n"
        "- Los Excel originales no se copiaron ni modificaron; `entrada/ARCHIVOS.md` conserva sus huellas.\n"
    )
    (root / "README.md").write_text(readme, encoding="utf-8")


def _refresh_archived_reports(database_path: Path, year: int, week: int) -> None:
    pattern = f"corrida_*_semana_{week:02d}"
    for root in DEFAULT_ARCHIVE_DIR.glob(pattern):
        if root.is_dir():
            generate_report(
                database_path, year=year, week=week,
                output_path=root / "salida" / f"Reporte_Disponibilidad_Semana{week}.html",
            )
            _write_llm_evidence(root, database_path, year, week)


class AppHandler(BaseHTTPRequestHandler):
    database_path = DEFAULT_DB_PATH
    password = ""
    session_secret = ""
    secure_cookie = False

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _session_csrf(self) -> str | None:
        if not self.password:
            return "local-session"
        cookies = self.headers.get("Cookie", "")
        token = next((part.split("=", 1)[1] for part in cookies.split("; ") if part.startswith("agent_session=")), "")
        return _read_session(token, self.session_secret) if token else None

    def _require_auth(self) -> str | None:
        csrf = self._session_csrf()
        if csrf is None:
            self._send_html(login_page(), HTTPStatus.UNAUTHORIZED)
        return csrf

    def _check_csrf(self, supplied: str, expected: str) -> bool:
        if not self.password:
            return True
        if hmac.compare_digest(supplied, expected):
            return True
        self._send_html(login_page("La sesión o el formulario vencieron. Ingresá nuevamente."), HTTPStatus.FORBIDDEN)
        return False

    def _home(self, message: str = "", error: bool = False, status: HTTPStatus = HTTPStatus.OK) -> None:
        csrf = self._require_auth()
        if csrf is not None:
            self._send_html(page(HistoryDatabase(self.database_path), csrf=csrf, message=message, error=error), status)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/salud":
            self._send_html("<!doctype html><meta charset='utf-8'><p>OK</p>")
            return
        if self._require_auth() is None:
            return
        if parsed.path == "/":
            self._home()
            return
        if parsed.path == "/reporte":
            try:
                query = parse_qs(parsed.query)
                year, week = int(query["year"][0]), int(query["week"][0])
                target = report_path(year, week)
                generate_report(self.database_path, year=year, week=week, output_path=target)
                content = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(content)
            except (KeyError, ValueError) as error:
                self._home(f"No se pudo abrir el reporte: {error}", True, HTTPStatus.NOT_FOUND)
            return
        self._home("Página no encontrada.", True, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            data = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            client = self.client_address[0]
            now = time.time()
            failures = [stamp for stamp in _LOGIN_FAILURES.get(client, []) if now - stamp < LOGIN_WINDOW_SECONDS]
            if len(failures) >= LOGIN_MAX_FAILURES:
                self._send_html(login_page("Demasiados intentos. Esperá 15 minutos."), HTTPStatus.TOO_MANY_REQUESTS)
                return
            supplied = data.get("password", [""])[0]
            if not self.password or not hmac.compare_digest(supplied, self.password):
                failures.append(now)
                _LOGIN_FAILURES[client] = failures
                self._send_html(login_page("Contraseña incorrecta."), HTTPStatus.UNAUTHORIZED)
                return
            _LOGIN_FAILURES.pop(client, None)
            token, _ = _make_session(self.session_secret)
            secure = "; Secure" if self.secure_cookie else ""
            self._redirect("/", f"agent_session={token}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Lax{secure}")
            return
        csrf = self._require_auth()
        if csrf is None:
            return
        if parsed.path == "/logout":
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            data = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            if not self._check_csrf(data.get("csrf", [""])[0], csrf):
                return
            secure = "; Secure" if self.secure_cookie else ""
            self._redirect("/", f"agent_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure}")
            return
        if parsed.path == "/interpretar":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = parse_qs(self.rfile.read(length).decode("utf-8"))
                if not self._check_csrf(data.get("csrf", [""])[0], csrf):
                    return
                year, week = int(data["year"][0]), int(data["week"][0])
                model = data.get("model", ["gpt-5.4-mini"])[0]
                effort = data.get("reasoning_effort", ["medium"])[0]
                if model not in MODEL_PRICES or effort not in {"none", "low", "medium", "high", "xhigh"}:
                    raise ValueError("La combinación de modelo y razonamiento no es válida.")
                count = interpret_week_with_openai(
                    self.database_path, year=year, week=week,
                    model=model, reasoning_effort=effort,
                )
                generate_report(self.database_path, year=year, week=week, output_path=report_path(year, week))
                _refresh_archived_reports(self.database_path, year, week)
                self._home(f"Interpretación LLM completada: {count} hallazgos preliminares.")
            except (KeyError, ValueError, LLMServiceError) as error:
                self._home(str(error), True, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path != "/procesar":
            self._home("Acción no encontrada.", True, HTTPStatus.NOT_FOUND)
            return
        try:
            fields, uploads = _parse_multipart(self)
            if not self._check_csrf(fields.get("csrf", ""), csrf):
                return
            year, week = int(fields["year"]), int(fields["week"])
            model = fields.get("model", "gpt-5.4-mini")
            effort = fields.get("reasoning_effort", "medium")
            if model not in MODEL_PRICES or effort not in {"none", "low", "medium", "high", "xhigh"}:
                raise InputValidationError("La combinación de modelo y razonamiento no es válida.")
            start_date, end_date = date.fromisoformat(fields["start_date"]), date.fromisoformat(fields["end_date"])
            database = HistoryDatabase(self.database_path)
            if database.week_exists(year, week):
                raise DuplicateWeekError(f"La semana {week}/{year} ya está cargada y no se duplicó.")
            required = {"notices", "notifications", "maintenance"}
            if set(uploads) != required:
                raise InputValidationError("Deben cargarse exactamente los tres Excel solicitados.")
            with tempfile.TemporaryDirectory(prefix="agente_mantenimiento_") as temp_name:
                paths: dict[str, Path] = {}
                for key in required:
                    filename, payload = uploads[key]
                    suffix = Path(filename).suffix.lower()
                    if suffix not in ALLOWED_EXTENSIONS or not payload:
                        raise InputValidationError(f"{filename}: sólo se aceptan archivos Excel .xlsx o .xlsm.")
                    path = Path(temp_name) / f"{key}{suffix}"
                    path.write_bytes(payload)
                    paths[key] = path
                validate_no_confidential_data(
                    (paths[key], uploads[key][0]) for key in ("notices", "notifications", "maintenance")
                )
                analysis = analyze_week(
                    year=year, week=week, start_date=start_date, end_date=end_date,
                    notices_path=paths["notices"], notifications_path=paths["notifications"],
                    maintenance_path=paths["maintenance"],
                )
                for key in required:
                    analysis["sources"][key]["name"] = uploads[key][0]
                database.save_analysis(analysis)
            llm_message = ""
            llm_error: str | None = None
            try:
                count = interpret_week_with_openai(
                    self.database_path, year=year, week=week, model=model,
                    reasoning_effort=effort,
                )
                llm_message = f" Interpretación LLM: {count} hallazgos preliminares, sujetos a revisión humana."
            except LLMServiceError as error:
                llm_error = str(error)
                llm_message = f" {error}"
            target = generate_report(self.database_path, year=year, week=week, output_path=report_path(year, week))
            _save_archive(
                analysis, year, week, target,
                database_path=self.database_path,
                requested_model=model,
                requested_effort=effort,
                llm_error=llm_error,
            )
            self._home(f"Semana {week}/{year} calculada y guardada.{llm_message}")
        except DuplicateWeekError as error:
            self._home(str(error), True, HTTPStatus.CONFLICT)
        except (KeyError, ValueError, InputValidationError, ConfidentialDataError) as error:
            self._home(f"No se pudo procesar la semana: {error}", True, HTTPStatus.BAD_REQUEST)
        except Exception as error:  # keep the browser usable while avoiding a raw traceback
            self._home(f"Error inesperado durante el procesamiento: {error}", True, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def serve(host: str = "127.0.0.1", port: int = 8000, database_path: Path = DEFAULT_DB_PATH) -> None:
    password = os.environ.get("AGENT_PASSWORD", "")
    session_secret = os.environ.get("SESSION_SECRET", "")
    public_host = host not in {"127.0.0.1", "localhost", "::1"}
    if public_host and (len(password) < 12 or len(session_secret) < 32):
        raise RuntimeError(
            "Para publicar el agente, configurá AGENT_PASSWORD (mínimo 12 caracteres) "
            "y SESSION_SECRET (mínimo 32 caracteres)."
        )
    AppHandler.database_path = Path(database_path).resolve()
    AppHandler.password = password
    AppHandler.session_secret = session_secret or secrets.token_urlsafe(32)
    AppHandler.secure_cookie = os.environ.get("PUBLIC_BASE_URL", "").lower().startswith("https://")
    server = ThreadingHTTPServer((host, port), AppHandler)
    actual_port = server.server_address[1]
    print(f"Agente disponible en http://{host}:{actual_port}", flush=True)
    print("Presioná Ctrl+C para detenerlo.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Página web local del agente de disponibilidad.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)
    serve(args.host, args.port, args.db)
    return 0
