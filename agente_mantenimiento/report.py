from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import EQUIPMENT
from .database import HistoryDatabase


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def fmt_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "No calculable"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_percent(value: float | None) -> str:
    return "No calculable" if value is None else f"{fmt_number(value)} %"


def _same_bridge_repeats(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for failure in failures:
        if failure["has_stop"] and failure["description_normalized"]:
            groups[(failure["equipment"], failure["description_normalized"])].append(failure)
    output = []
    for (equipment, _), rows in groups.items():
        if len(rows) < 2:
            continue
        output.append({
            "equipment": equipment,
            "descriptions": [row["description"] for row in rows],
            "weeks": sorted({f"{row['week']}/{row['year']}" for row in rows}),
            "count": len(rows),
            "causes": [row["documented_cause"] or "Sin causa documentada" for row in rows],
            "interventions": [" | ".join(row["interventions"]) or "Sin notificación vinculable" for row in rows],
        })
    return sorted(output, key=lambda row: (EQUIPMENT.index(row["equipment"]), -row["count"]))


def _cross_bridge_candidates(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for failure in failures:
        if failure["has_stop"]:
            groups[failure["category"]].append(failure)
    output = []
    for category, rows in groups.items():
        equipment = sorted({row["equipment"] for row in rows}, key=EQUIPMENT.index)
        if len(equipment) < 2:
            continue
        output.append({
            "category": category,
            "equipment": equipment,
            "weeks": sorted({f"{row['week']}/{row['year']}" for row in rows}),
            "count": len(rows),
            "descriptions": [f"{row['equipment']}: {row['description']}" for row in rows],
        })
    return sorted(output, key=lambda row: (-row["count"], row["category"]))


def _chart_points(data: dict[str, Any]) -> list[dict[str, Any]]:
    points = []
    for week in data["weeks"]:
        points.append({
            "year": week["year"], "week": week["week"], "label": f"S{week['week']}/{week['year']}",
            "level": "global", "key": "Global", "room": "", "series": "",
            "maintenance_hours": week["global_maintenance_hours"],
            "stop_hours": week["global_stop_hours"],
            "stoppage_count": week["global_stoppage_count"],
            "availability": week["global_availability"],
        })
    for row in data["aggregate_history"]:
        room = row["aggregate_key"] if row["level"] == "room" else ""
        series = row["aggregate_key"] if row["level"] == "series" else ("A" if room in ("1", "2") else "B")
        points.append({
            "year": row["year"], "week": row["week"], "label": f"S{row['week']}/{row['year']}",
            "level": row["level"], "key": row["aggregate_key"], "room": room,
            "series": series, "maintenance_hours": row["maintenance_hours"],
            "stop_hours": row["stop_hours"], "stoppage_count": row["stoppage_count"],
            "availability": row["availability"],
        })
    for row in data["equipment_history"]:
        points.append({
            "year": row["year"], "week": row["week"], "label": f"S{row['week']}/{row['year']}",
            "level": "equipment", "key": row["equipment"], "room": str(row["room"]),
            "series": row["series"], "maintenance_hours": row["maintenance_hours"],
            "stop_hours": row["stop_hours"], "stoppage_count": row["stoppage_count"],
            "availability": row["availability"],
        })
    return points


def generate_report(
    database_path: str | Path,
    *,
    year: int,
    week: int,
    output_path: str | Path,
) -> Path:
    database = HistoryDatabase(database_path)
    data = database.load_report_data(year, week)
    current = data["current"]
    current_id = current["id"]
    current_equipment = [row for row in data["equipment_history"] if row["week_id"] == current_id]
    current_aggregates = [row for row in data["aggregate_history"] if row["week_id"] == current_id]
    current_failures = [row for row in data["failures"] if row["week_id"] == current_id]
    current_rooms = [row for row in current_aggregates if row["level"] == "room"]
    current_series = [row for row in current_aggregates if row["level"] == "series"]
    stopped_failures = [row for row in current_failures if row["has_stop"]]
    repeat_groups = _same_bridge_repeats(data["failures"])
    cross_candidates = _cross_bridge_candidates(data["failures"])
    chart_points = _chart_points(data)
    week_count = len(data["weeks"])
    previous_weeks = [row for row in data["weeks"] if (row["year"], row["week"]) < (year, week)]
    previous = previous_weeks[-1] if previous_weeks else None

    equipment_rows = "".join(
        f"""
        <tr><td class="tag">{esc(row['equipment'])}</td><td>{row['room']}</td><td>{row['series']}</td>
        <td class="num">{fmt_number(row['maintenance_hours'])}</td><td class="num">{fmt_number(row['available_hours'])}</td>
        <td class="num">{row['stoppage_count']}</td><td class="num">{fmt_number(row['stop_hours'])}</td>
        <td class="num strong">{fmt_percent(row['availability'])}</td>
        <td>{esc('; '.join(json.loads(row['failure_descriptions_json'])) or 'Sin detenciones')}</td></tr>
        """
        for row in current_equipment
    )

    def aggregate_rows(rows: list[dict[str, Any]], label: str) -> str:
        return "".join(
            f"<tr><td>{label} {esc(row['aggregate_key'])}</td><td class='num'>{fmt_number(row['calendar_hours'])}</td>"
            f"<td class='num'>{fmt_number(row['maintenance_hours'])}</td><td class='num'>{fmt_number(row['available_hours'])}</td>"
            f"<td class='num'>{fmt_number(row['stop_hours'])}</td><td class='num strong'>{fmt_percent(row['availability'])}</td></tr>"
            for row in rows
        )

    failure_rows = "".join(
        f"""
        <tr data-week="{row['week']}" data-equipment="{esc(row['equipment'])}" data-room="{row['room']}" data-series="{row['series']}">
        <td class="tag">{esc(row['equipment'])}</td><td>{esc(row['notice_number'])}</td><td>{esc(row['order_number'])}</td>
        <td class="num">{fmt_number(row['stop_hours'])}</td><td>{esc(row['category'])}</td>
        <td>{esc(row['description'])}</td><td>{esc(row['documented_cause'] or 'Sin causa documentada')}</td>
        <td>{'<br>'.join(esc(text) for text in row['interventions']) or '<span class="muted">Sin notificación vinculable</span>'}</td></tr>
        """
        for row in stopped_failures
    )

    issue_rows = "".join(
        f"<tr><td>{esc(row['severity'])}</td><td>{esc(row['issue_type'])}</td><td>{esc(row['source'])}</td>"
        f"<td>{esc(row['equipment'] or '')}</td><td>{esc(row['detail'])}</td></tr>"
        for row in data["current_issues"]
    ) or "<tr><td colspan='5'>No se detectaron observaciones de validación.</td></tr>"

    repeat_rows = "".join(
        f"<tr><td class='tag'>{esc(row['equipment'])}</td><td>{'<br>'.join(esc(value) for value in row['descriptions'])}</td>"
        f"<td>{esc(', '.join(row['weeks']))}</td><td class='num'>{row['count']}</td>"
        f"<td>{'<br>'.join(esc(value) for value in row['causes'])}</td>"
        f"<td>{'<br>'.join(esc(value) for value in row['interventions'])}</td><td>Sí</td></tr>"
        for row in repeat_groups
    ) or "<tr><td colspan='7'>Todavía no hay descripciones repetidas en un mismo puente.</td></tr>"

    candidate_rows = "".join(
        f"<tr><td>{esc(row['category'])}</td><td>{esc(', '.join(row['equipment']))}</td>"
        f"<td>{esc(', '.join(row['weeks']))}</td><td class='num'>{row['count']}</td>"
        f"<td>{'<br>'.join(esc(value) for value in row['descriptions'])}</td>"
        f"<td>Candidato preparado por Python. Requiere interpretación del LLM y revisión humana.</td></tr>"
        for row in cross_candidates
    ) or "<tr><td colspan='6'>No hay candidatos entre puentes diferentes.</td></tr>"

    finding_rows = "".join(
        f"<tr><td>{'Mismo puente' if row['relation_type'] == 'same_bridge' else 'Entre puentes'}</td><td>{esc(row['title'])}</td>"
        f"<td>{esc(', '.join(row['notice_numbers']))}</td><td>{esc(row['confidence'])}</td>"
        f"<td>{esc(row['rationale'])}</td><td>{esc(row['human_review'])}</td></tr>"
        for row in data["llm_findings"]
    ) or "<tr><td colspan='6'>No se cargaron interpretaciones del LLM. Los valores numéricos permanecen bajo control exclusivo de Python.</td></tr>"

    llm_status_html = (
        f"<div class='notice'><strong>Interpretación preliminar del LLM: {len(data['llm_findings'])} hallazgos.</strong> "
        "No es determinante ni constituye un diagnóstico final. Todos los hallazgos requieren revisión y validación humana.</div>"
        if data["llm_findings"]
        else "<div class='notice warning'><strong>Corrida incompleta: interpretación LLM pendiente.</strong> "
             "El reporte no debe considerarse final hasta incorporar la interpretación preliminar y su revisión humana.</div>"
    )

    comparison_html = (
        f"""
        <div class="notice"><strong>Comparación inicial con S{previous['week']}/{previous['year']}.</strong>
        Disponibilidad global: {fmt_percent(previous['global_availability'])} → {fmt_percent(current['global_availability'])}
        ({fmt_number(current['global_availability'] - previous['global_availability'])} puntos porcentuales).
        Horas de parada: {fmt_number(previous['global_stop_hours'])} → {fmt_number(current['global_stop_hours'])} h.
        Detenciones: {previous['global_stoppage_count']} → {current['global_stoppage_count']}.
        Esta comparación no se presenta como tendencia.</div>
        """
        if previous
        else "<div class='notice warning'><strong>Sin historial suficiente.</strong> Esta es la primera semana almacenada. No se calculan comparaciones ni tendencias.</div>"
    )

    history_note = (
        "Existe una sola semana almacenada. Los gráficos muestran el valor inicial y no una tendencia."
        if week_count == 1
        else (
            f"La base contiene {week_count} semanas y {len(data['llm_findings'])} interpretaciones del LLM, "
            "todas sujetas a revisión humana."
            if data["llm_findings"]
            else f"La base contiene {week_count} semanas. La interpretación del LLM está pendiente."
        )
    )

    embedded = json.dumps({
        "points": chart_points,
        "failures": [
            {
                "year": row["year"], "week": row["week"], "equipment": row["equipment"],
                "room": str(row["room"]), "series": row["series"], "category": row["category"],
                "description": row["description"], "stop_hours": row["stop_hours"],
            }
            for row in data["failures"] if row["has_stop"]
        ],
    }, ensure_ascii=False).replace("</", "<\\/")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte semanal de disponibilidad S{week}/{year}</title>
<style>
:root{{--navy:#17324d;--blue:#28658f;--ink:#1b2733;--muted:#60707d;--line:#d8e0e6;--soft:#f3f6f8;--paper:#fff;--warning:#8a4b08;--warning-bg:#fff4e5}}
*{{box-sizing:border-box}}body{{margin:0;background:#eef2f5;color:var(--ink);font:14px/1.45 Arial,sans-serif}}.page{{max-width:1500px;margin:auto;background:var(--paper);min-height:100vh}}
header{{padding:28px 34px 22px;background:var(--navy);color:#fff}}header h1{{margin:0 0 6px;font-size:25px}}header p{{margin:0;color:#dce7ef}}
.tabs{{display:flex;border-bottom:1px solid var(--line);background:#fafbfd;padding:0 24px;position:sticky;top:0;z-index:5}}.tab{{border:0;border-bottom:3px solid transparent;background:transparent;padding:15px 18px 12px;font-weight:600;color:var(--muted);cursor:pointer}}.tab[aria-selected=true]{{color:var(--navy);border-bottom-color:var(--blue)}}
main{{padding:28px 34px 48px}}.panel[hidden]{{display:none}}h2{{color:var(--navy);font-size:19px;margin:30px 0 12px}}h3{{color:var(--navy);font-size:15px;margin:20px 0 8px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.box{{border:1px solid var(--line);border-radius:6px;padding:14px 16px}}.label{{color:var(--muted);font-size:12px;text-transform:uppercase}}.value{{color:var(--navy);font-size:23px;font-weight:600;margin-top:3px;font-variant-numeric:tabular-nums}}.sub,.muted{{color:var(--muted);font-size:12px}}
.notice{{border-left:4px solid var(--blue);background:var(--soft);padding:12px 14px;margin:14px 0}}.warning{{border-left-color:var(--warning);background:var(--warning-bg)}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:6px}}table{{width:100%;border-collapse:collapse;min-width:720px}}th{{background:var(--soft);color:var(--navy);text-align:left;font-size:12px;padding:9px 10px;border-bottom:1px solid var(--line);position:sticky;top:0}}td{{padding:9px 10px;border-bottom:1px solid #e7ecef;vertical-align:top}}.num{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}.tag,.strong{{font-weight:600;white-space:nowrap}}
.filters{{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:12px;padding:14px;background:var(--soft);border:1px solid var(--line);border-radius:6px}}label{{font-size:12px;font-weight:600;color:var(--navy)}}select{{display:block;width:100%;margin-top:5px;padding:8px;border:1px solid #b7c3cd;border-radius:4px;background:#fff}}
.charts{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:18px 0}}.chart{{border:1px solid var(--line);border-radius:6px;padding:12px}}.chart h3{{margin:0 0 8px}}.chart svg{{width:100%;height:240px;display:block}}.axis{{stroke:#9eabb6;stroke-width:1}}.gridline{{stroke:#e4e9ed;stroke-width:1}}.series-line{{fill:none;stroke:var(--blue);stroke-width:2}}.point{{fill:var(--blue)}}.chart-label{{fill:var(--muted);font-size:11px}}.chart-value{{fill:var(--navy);font-size:12px;font-weight:600}}
footer{{border-top:1px solid var(--line);padding:18px 34px;color:var(--muted);font-size:12px}}@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}.two,.charts{{grid-template-columns:1fr}}.filters{{grid-template-columns:repeat(2,1fr)}}main{{padding:22px 18px 36px}}header{{padding:24px 18px}}}}
</style></head><body><div class="page">
<header><h1>Reporte semanal de disponibilidad</h1><p>Puentes grúa P‑MG · Semana {week}/{year} · {current['start_date']} al {current['end_date']}</p></header>
<nav class="tabs" role="tablist"><button class="tab" id="tab-current" role="tab" aria-selected="true" aria-controls="current">1. Semana procesada</button><button class="tab" id="tab-history" role="tab" aria-selected="false" aria-controls="history">2. Histórico y recurrencias</button></nav>
<main><section class="panel" id="current" role="tabpanel" aria-labelledby="tab-current">
<div class="grid"><div class="box"><div class="label">Semana</div><div class="value">{week}/{year}</div><div class="sub">{current['start_date']} al {current['end_date']}</div></div>
<div class="box"><div class="label">Disponibilidad global</div><div class="value">{fmt_percent(current['global_availability'])}</div><div class="sub">Cálculo agregado</div></div>
<div class="box"><div class="label">Horas de parada</div><div class="value">{fmt_number(current['global_stop_hours'])} h</div><div class="sub">{current['global_stoppage_count']} detenciones</div></div>
<div class="box"><div class="label">Mantenimiento</div><div class="value">{fmt_number(current['global_maintenance_hours'])} h</div><div class="sub">Tiempo disponible {fmt_number(current['global_available_hours'])} h</div></div></div>
{comparison_html}
<div class="two"><div><h2>Disponibilidad por serie</h2><div class="table-wrap"><table><thead><tr><th>Serie</th><th class="num">Calendario h</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Parada h</th><th class="num">Disponibilidad</th></tr></thead><tbody>{aggregate_rows(current_series,'Serie')}</tbody></table></div></div>
<div><h2>Disponibilidad por sala</h2><div class="table-wrap"><table><thead><tr><th>Sala</th><th class="num">Calendario h</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Parada h</th><th class="num">Disponibilidad</th></tr></thead><tbody>{aggregate_rows(current_rooms,'Sala')}</tbody></table></div></div></div>
<h2>Disponibilidad por puente</h2><div class="table-wrap"><table><thead><tr><th>Equipo</th><th>Sala</th><th>Serie</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Detenciones</th><th class="num">Parada h</th><th class="num">Disponibilidad</th><th>Fallas con detención</th></tr></thead><tbody>{equipment_rows}</tbody></table></div>
<h2>Detenciones y notificaciones vinculadas</h2><div class="table-wrap"><table><thead><tr><th>Equipo</th><th>Aviso</th><th>Orden</th><th class="num">Parada h</th><th>Categoría</th><th>Descripción original</th><th>Causa documentada</th><th>Intervención</th></tr></thead><tbody>{failure_rows}</tbody></table></div>
<h2>Validación</h2><div class="table-wrap"><table><thead><tr><th>Severidad</th><th>Control</th><th>Fuente</th><th>Equipo</th><th>Detalle</th></tr></thead><tbody>{issue_rows}</tbody></table></div>
</section>
<section class="panel" id="history" role="tabpanel" aria-labelledby="tab-history" hidden><h2>Histórico</h2><div class="notice {'warning' if week_count == 1 else ''}"><strong>Semanas almacenadas: {week_count}.</strong> {history_note}</div>
<div class="filters"><label>Semana<select id="filter-week"><option value="">Todas</option>{''.join(f'<option value="{row["year"]}-{row["week"]}">S{row["week"]}/{row["year"]}</option>' for row in data['weeks'])}</select></label>
<label>Puente<select id="filter-equipment"><option value="">Todos</option>{''.join(f'<option>{tag}</option>' for tag in EQUIPMENT)}</select></label>
<label>Sala<select id="filter-room"><option value="">Todas</option>{''.join(f'<option>{room}</option>' for room in range(1,5))}</select></label>
<label>Serie<select id="filter-series"><option value="">Todas</option><option>A</option><option>B</option></select></label></div>
<p id="selection-note" class="muted">Vista global de todas las semanas.</p>
<div class="charts"><div class="chart"><h3>Horas de parada por semana</h3><svg id="chart-stop" role="img" aria-label="Horas de parada por semana"></svg></div><div class="chart"><h3>Disponibilidad por semana</h3><svg id="chart-availability" role="img" aria-label="Disponibilidad por semana"></svg></div><div class="chart"><h3>Detenciones por semana</h3><svg id="chart-count" role="img" aria-label="Cantidad de detenciones por semana"></svg></div></div>
<h2>Valores históricos seleccionados</h2><div class="table-wrap"><table><thead><tr><th>Semana</th><th>Nivel</th><th>Elemento</th><th class="num">Mantenimiento h</th><th class="num">Parada h</th><th class="num">Detenciones</th><th class="num">Disponibilidad</th></tr></thead><tbody id="history-body"></tbody></table></div>
<h2>Interpretación preliminar del LLM</h2>{llm_status_html}<div class="notice">El LLM relaciona los textos originales, las causas documentadas y las intervenciones vinculadas. No modifica los cálculos, no confirma causalidad y no reemplaza el criterio técnico del responsable.</div><div class="table-wrap"><table><thead><tr><th>Alcance</th><th>Hallazgo</th><th>Avisos relacionados</th><th>Confianza</th><th>Interpretación</th><th>Revisión humana obligatoria</th></tr></thead><tbody>{finding_rows}</tbody></table></div>
<h2>Fallas repetidas en el mismo puente</h2><div class="table-wrap"><table><thead><tr><th>Puente</th><th>Descripciones originales</th><th>Semanas</th><th class="num">Cantidad</th><th>Causas documentadas</th><th>Intervenciones</th><th>Revisión humana</th></tr></thead><tbody>{repeat_rows}</tbody></table></div>
<h2>Candidatos de fallas similares entre puentes</h2><div class="notice">Python agrupa candidatos por categoría y conserva los textos originales. No afirma causalidad ni confirma similitud técnica. Esa decisión corresponde al LLM y a la revisión humana.</div><div class="table-wrap"><table><thead><tr><th>Categoría candidata</th><th>Puentes</th><th>Semanas</th><th class="num">Eventos</th><th>Descripciones originales</th><th>Estado</th></tr></thead><tbody>{candidate_rows}</tbody></table></div>
</section></main><footer>Los cálculos y los datos de los gráficos fueron preparados por Python y almacenados en SQLite. La interpretación del LLM es preliminar, no determinante y requiere siempre revisión humana; no puede modificar horas, cantidades ni disponibilidades.</footer></div>
<script>
const DATA={embedded};
const q=id=>document.getElementById(id);document.querySelectorAll('.tab').forEach(tab=>tab.addEventListener('click',()=>{{document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',String(t===tab)));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==tab.getAttribute('aria-controls'));if(tab.id==='tab-history')updateHistory();}}));
['filter-week','filter-equipment','filter-room','filter-series'].forEach(id=>q(id).addEventListener('change',updateHistory));
function selection(){{const equipment=q('filter-equipment').value,room=q('filter-room').value,series=q('filter-series').value,week=q('filter-week').value;let level='global',key='Global';if(equipment){{level='equipment';key=equipment}}else if(room){{level='room';key=room}}else if(series){{level='series';key=series}}let rows=DATA.points.filter(r=>r.level===level&&r.key===key);if(week){{const [year,w]=week.split('-').map(Number);rows=rows.filter(r=>r.year===year&&r.week===w)}}rows.sort((a,b)=>a.year-b.year||a.week-b.week);return{{rows,level,key,week}}}}
function fmt(value,digits=2){{return value==null?'No calculable':value.toLocaleString('es-AR',{{minimumFractionDigits:digits,maximumFractionDigits:digits}})}}
function draw(id,rows,field,unit,zeroBase=true){{const svg=q(id),w=420,h=240,m={{l:58,r:20,t:25,b:48}},iw=w-m.l-m.r,ih=h-m.t-m.b;svg.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);if(!rows.length){{svg.innerHTML='<text class="chart-label" x="210" y="120" text-anchor="middle">Sin datos para el filtro</text>';return}}const values=rows.map(r=>r[field]).filter(v=>v!=null);let min=zeroBase?0:Math.min(...values),max=Math.max(...values);if(field==='availability'){{min=Math.min(90,min);max=100}}if(max===min)max=min+1;const x=i=>rows.length===1?m.l+iw/2:m.l+iw*i/(rows.length-1),y=v=>m.t+ih-(v-min)/(max-min)*ih;let grid='';for(let i=0;i<=4;i++){{const value=min+(max-min)*i/4,yy=y(value);grid+=`<line class="gridline" x1="${{m.l}}" y1="${{yy}}" x2="${{w-m.r}}" y2="${{yy}}"/><text class="chart-label" x="${{m.l-7}}" y="${{yy+4}}" text-anchor="end">${{fmt(value,field==='stoppage_count'?0:1)}}</text>`}}const valid=rows.map((r,i)=>({{r,i,v:r[field]}})).filter(p=>p.v!=null);const path=valid.map((p,index)=>`${{index?'L':'M'}} ${{x(p.i)}} ${{y(p.v)}}`).join(' ');const marks=valid.map(p=>`<circle class="point" cx="${{x(p.i)}}" cy="${{y(p.v)}}" r="4"><title>${{p.r.label}}: ${{fmt(p.v)}} ${{unit}}</title></circle><text class="chart-value" x="${{x(p.i)}}" y="${{Math.max(13,y(p.v)-9)}}" text-anchor="middle">${{fmt(p.v)}}</text>`).join('');const labels=rows.map((r,i)=>`<text class="chart-label" x="${{x(i)}}" y="${{h-18}}" text-anchor="middle">${{r.label}}</text>`).join('');svg.innerHTML=`${{grid}}<line class="axis" x1="${{m.l}}" y1="${{m.t+ih}}" x2="${{w-m.r}}" y2="${{m.t+ih}}"/><path class="series-line" d="${{path}}"/>${{marks}}${{labels}}`}}
function updateHistory(){{const s=selection();q('selection-note').textContent=`Nivel: ${{s.level}} · Elemento: ${{s.key}} · ${{s.week?'una semana':'todas las semanas'}}`;draw('chart-stop',s.rows,'stop_hours','h',true);draw('chart-availability',s.rows,'availability','%',false);draw('chart-count',s.rows,'stoppage_count','',true);q('history-body').innerHTML=s.rows.map(r=>`<tr><td>${{r.label}}</td><td>${{r.level}}</td><td>${{r.key}}</td><td class="num">${{fmt(r.maintenance_hours)}}</td><td class="num">${{fmt(r.stop_hours)}}</td><td class="num">${{fmt(r.stoppage_count,0)}}</td><td class="num strong">${{fmt(r.availability)}} %</td></tr>`).join('')||'<tr><td colspan="7">Sin datos para el filtro seleccionado.</td></tr>'}}
updateHistory();
</script></body></html>"""
    output_path.write_text(document, encoding="utf-8")
    return output_path
