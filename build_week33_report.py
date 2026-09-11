from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Trabajo final" / "semana34_datos.json"
OUT_DIR = ROOT / "Trabajo final" / "corridas" / "corrida_06_semana_34_05_09_26" / "salida"
OUT_PATH = OUT_DIR / "Reporte_Disponibilidad_Semana34.html"


def esc(value):
    return html.escape("" if value is None else str(value))


def fmt_num(value, decimals=2):
    if value is None:
        return "No calculable"
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value):
    return "No calculable" if value is None else f"{fmt_num(value)} %"


def fmt_dt(value):
    if not value:
        return "Sin dato"
    return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M")


def join_text(items):
    clean = [esc(x) for x in items if x]
    return "<br>".join(clean) if clean else '<span class="muted">Sin notificación vinculable</span>'


def event_by_notice(data, notice):
    return next(e for e in data["avisos"] if e["aviso"] == notice)


def recurrence(data, title, notices, source, confidence, justification, action):
    events = [event_by_notice(data, n) for n in notices]
    return {
        "categoria": title,
        "fuente": source,
        "descripciones": [e["descripcion"] for e in events],
        "equipos": sorted({e["equipo"] for e in events}, key=lambda x: [r["equipo"] for r in data["puentes"]].index(x)),
        "semanas": f"{data['periodo']['semana']}/{data['periodo']['anio']}",
        "cantidad": len(events),
        "causas": [e["causa"] or "Sin causa documentada" for e in events],
        "intervenciones": [" | ".join(e["intervenciones"]) if e["intervenciones"] else "Sin notificación vinculable" for e in events],
        "confianza": confidence,
        "justificacion": justification,
        "accion": action,
    }


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    stopped = [e for e in data["avisos"] if e["parada"]]
    total_stops = sum(e["duracion"] for e in stopped if e["duracion_valida"])
    total_events = len(data["avisos"])
    linked_stops = sum(1 for e in stopped if e["notificacion_encontrada"])
    impact = next(r for r in data["puentes"] if r["equipo"] == "P-MG22")
    impact_room = next(r for r in data["salas"] if r["nombre"] == "Sala 2")

    recurrences = [
        recurrence(data, "Descenso de picador en P-MG31", ["800901053", "800901358"],
                   "Mismo puente y descripciones originales similares",
                   "Alta para repetición del síntoma; baja para causa común",
                   "Ambos avisos declaran que el picador no baja, pero registran causas e intervenciones distintas: calibración de peso y cambio de celda de carga.",
                   "Sí. Verificar la cadena de medición de carga y el mando de descenso antes de concluir que existe una causa única."),
        recurrence(data, "Balanza en P-MG33", ["800900892", "800901552"],
                   "Mismo puente y descripciones originales similares",
                   "Alta para asociación del subsistema; baja para causa común",
                   "Los dos avisos mencionan la balanza; las causas documentadas son falla electrónica y falso contacto.",
                   "Sí. Revisar alimentación, conexiones, celdas y registros de calibración, conservando las causas como hipótesis separadas."),
        recurrence(data, "Picador en P-MG13", ["800900838", "800901082"],
                   "Mismo puente y descripciones funcionalmente similares",
                   "Alta para repetición del síntoma; baja para causa común",
                   "Los avisos indican que el picador no funciona o no pica; uno registra falta de aceite y otro aflojamiento.",
                   "Sí. Confirmar lubricación, ajuste y prueba funcional documentada después de cada intervención."),
        recurrence(data, "Giro de percha en varios puentes", ["800901499", "800901609", "800901642", "800901653"],
                   "Distintos puentes con descripciones funcionalmente similares",
                   "Media para categoría funcional; no prueba causa compartida",
                   "Cuatro avisos en P-MG11, P-MG22 y P-MG23 declaran que la percha no gira; las causas e intervenciones no son uniformes.",
                   "Sí. Comparar pantógrafos, códigos de variador y conexiones por equipo sin fusionar causas ni tiempos."),
        recurrence(data, "Condensador de precarga de ATV", ["800901598", "800901625"],
                   "Distintos puentes con el mismo texto de notificación",
                   "Alta para asociación del código; no determina causa raíz",
                   "P-MG12 y P-MG23 registran aparejo de 15 TN que no baja y la misma intervención: reset de ATV por condensador de precarga.",
                   "Sí. Confirmar modelo de ATV, tensión de red, cableado, puesta a tierra e historial del bus de continua según el procedimiento del fabricante."),
    ]

    bridge_rows = []
    for r in data["puentes"]:
        observations = []
        if r["equipo"] == "P-MG22":
            observations.append("Concentra 22,52 h de parada; el aviso 800901556 aporta 21,07 h.")
        if r["fallas"]:
            observations.append("Fallas con detención: " + "; ".join(r["fallas"]))
        else:
            observations.append("Sin avisos con detención en el período.")
        bridge_rows.append(f"""
          <tr>
            <td class="tag">{esc(r['equipo'])}</td><td>{r['sala']}</td><td>{r['serie']}</td>
            <td class="num">{fmt_num(r['calendario'])}</td><td class="num">{fmt_num(r['mantenimiento'])}</td>
            <td class="num">{fmt_num(r['tiempo_disponible'])}</td><td class="num">{r['detenciones']}</td>
            <td class="num">{fmt_num(r['paradas'])}</td><td class="num strong">{fmt_pct(r['disponibilidad'])}</td>
            <td>{esc(' '.join(observations))}</td>
          </tr>""")

    failure_rows = []
    tag_order = {tag: i for i, tag in enumerate([r["equipo"] for r in data["puentes"]])}
    for e in sorted(stopped, key=lambda x: (tag_order[x["equipo"]], x["fila"])):
        review = "Revisar vinculación: orden sin notificación." if not e["notificacion_encontrada"] else "Validación humana de causa y cierre."
        failure_rows.append(f"""
          <tr data-week="34" data-bridge="{esc(e['equipo'])}" data-series="{data['puentes'][tag_order[e['equipo']]]['serie']}" data-room="{data['puentes'][tag_order[e['equipo']]]['sala']}" data-category="{esc(e['categoria'])}">
            <td class="tag">{esc(e['equipo'])}</td><td>{esc(e['aviso'])}</td><td>{esc(e['orden'])}</td>
            <td>{esc(fmt_dt(e['inicio']))}</td><td class="num">{fmt_num(e['duracion'])}</td>
            <td>{esc(e['categoria'])}</td><td>{esc(e['descripcion'])}</td><td>{esc(e['causa'] or 'Sin causa documentada')}</td>
            <td>{join_text(e['intervenciones'])}</td><td>{esc(review)}</td>
          </tr>""")

    recurrence_rows = []
    for r in recurrences:
        recurrence_rows.append(f"""
          <tr data-week="34" data-bridge="{'|'.join(r['equipos'])}" data-series="{'|'.join(sorted({data['puentes'][tag_order[t]]['serie'] for t in r['equipos']}))}" data-room="{'|'.join(str(data['puentes'][tag_order[t]]['sala']) for t in r['equipos'])}" data-category="{esc(r['categoria'])}">
            <td>{esc(r['categoria'])}</td><td>{esc(r['fuente'])}</td><td>{'<br>'.join(esc(x) for x in r['descripciones'])}</td>
            <td>{esc(', '.join(r['equipos']))}</td><td>{esc(r['semanas'])}</td><td class="num">{r['cantidad']}</td>
            <td>{'<br>'.join(esc(x) for x in r['causas'])}</td><td>{'<br>'.join(esc(x) for x in r['intervenciones'])}</td>
            <td>{esc(r['confianza'])}</td><td>{esc(r['justificacion'])}</td><td>{esc(r['accion'])}</td>
          </tr>""")

    aggregate_rows = lambda rows: "".join(
        f"<tr><td>{esc(r['nombre'])}</td><td class='num'>{fmt_num(r['calendario'])}</td><td class='num'>{fmt_num(r['mantenimiento'])}</td><td class='num'>{fmt_num(r['tiempo_disponible'])}</td><td class='num'>{fmt_num(r['paradas'])}</td><td class='num strong'>{fmt_pct(r['disponibilidad'])}</td></tr>"
        for r in rows
    )

    categories = sorted({e["categoria"] for e in stopped})
    data_js = json.dumps({"bridges": data["puentes"], "events": stopped}, ensure_ascii=False).replace("</", "<\\/")

    document = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reporte semanal de disponibilidad — Semana 34/2026</title>
  <style>
    :root {{ --navy:#17324d; --blue:#265f87; --ink:#1b2733; --muted:#5d6a76; --line:#d9e0e6; --soft:#f3f6f8; --paper:#ffffff; --warn:#8a4b08; --warn-bg:#fff4e5; --risk:#9a2f2f; --risk-bg:#fff0f0; --good:#226b4b; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#eef2f5; color:var(--ink); font:14px/1.45 Arial, Helvetica, sans-serif; }}
    .page {{ max-width:1500px; margin:0 auto; background:var(--paper); min-height:100vh; box-shadow:0 0 24px rgba(23,50,77,.08); }}
    header {{ padding:28px 34px 22px; background:var(--navy); color:#fff; }}
    header h1 {{ margin:0 0 6px; font-size:25px; font-weight:600; }}
    header p {{ margin:0; color:#d9e6ef; }}
    .tabs {{ display:flex; gap:0; border-bottom:1px solid var(--line); background:#fafbfd; padding:0 24px; position:sticky; top:0; z-index:10; }}
    .tab {{ appearance:none; border:0; border-bottom:3px solid transparent; background:transparent; padding:15px 18px 12px; font-weight:600; color:var(--muted); cursor:pointer; }}
    .tab[aria-selected="true"] {{ color:var(--navy); border-bottom-color:var(--blue); }}
    main {{ padding:28px 34px 48px; }}
    .panel[hidden] {{ display:none; }}
    h2 {{ color:var(--navy); font-size:19px; margin:30px 0 12px; }}
    h3 {{ color:var(--navy); font-size:15px; margin:20px 0 8px; }}
    .meta, .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .box {{ border:1px solid var(--line); border-radius:6px; padding:14px 16px; background:#fff; }}
    .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.03em; }}
    .value {{ color:var(--navy); font-size:23px; font-weight:600; margin-top:3px; font-variant-numeric:tabular-nums; }}
    .sub {{ color:var(--muted); font-size:12px; margin-top:3px; }}
    .notice {{ border-left:4px solid var(--blue); background:var(--soft); padding:12px 14px; margin:14px 0; }}
    .notice.warning {{ border-left-color:var(--warn); background:var(--warn-bg); }}
    .notice.risk {{ border-left-color:var(--risk); background:var(--risk-bg); }}
    .tables-two {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; min-width:720px; }}
    th {{ background:var(--soft); color:var(--navy); text-align:left; font-size:12px; padding:9px 10px; border-bottom:1px solid var(--line); position:sticky; top:0; }}
    td {{ padding:9px 10px; border-bottom:1px solid #e7ecef; vertical-align:top; }}
    tbody tr:last-child td {{ border-bottom:0; }}
    tbody tr:hover {{ background:#f8fafb; }}
    .num {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }}
    .tag, .strong {{ font-weight:600; white-space:nowrap; }}
    .muted {{ color:var(--muted); }}
    .actions {{ margin:0; padding-left:20px; }} .actions li {{ margin:7px 0; }}
    .filters {{ display:grid; grid-template-columns:repeat(5,minmax(130px,1fr)); gap:12px; padding:14px; border:1px solid var(--line); background:var(--soft); border-radius:6px; }}
    label {{ display:block; font-size:12px; font-weight:600; color:var(--navy); }}
    select {{ width:100%; margin-top:5px; padding:8px; border:1px solid #b7c3cd; border-radius:4px; background:#fff; color:var(--ink); }}
    .charts {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; margin:18px 0; }}
    .chart {{ border:1px solid var(--line); border-radius:6px; padding:12px; }}
    .chart h3 {{ margin:0 0 8px; }}
    .chart svg {{ width:100%; height:235px; display:block; }}
    .axis {{ stroke:#9eabb6; stroke-width:1; }} .bar {{ fill:var(--blue); }} .chart-label {{ fill:var(--muted); font-size:11px; }} .chart-value {{ fill:var(--navy); font-size:13px; font-weight:600; }}
    .source-list li {{ margin:7px 0; }} a {{ color:#1b5f91; }}
    footer {{ border-top:1px solid var(--line); padding:18px 34px; color:var(--muted); font-size:12px; }}
    @media (max-width:900px) {{ .meta,.kpis {{ grid-template-columns:repeat(2,1fr); }} .tables-two,.charts {{ grid-template-columns:1fr; }} .filters {{ grid-template-columns:repeat(2,1fr); }} main {{ padding:22px 18px 36px; }} header {{ padding:24px 18px; }} }}
    @media print {{ body {{ background:#fff; }} .page {{ box-shadow:none; }} .tabs,.filters {{ display:none; }} .panel[hidden] {{ display:block; }} th {{ position:static; }} .table-wrap {{ overflow:visible; }} }}
  </style>
</head>
<body>
<div class="page">
  <header>
    <h1>Reporte semanal de disponibilidad</h1>
    <p>Puentes grúa P‑MG · Semana 34/2026 · 17/08/2026 al 23/08/2026</p>
  </header>
  <nav class="tabs" role="tablist" aria-label="Secciones del reporte">
    <button class="tab" id="tab-week" role="tab" aria-selected="true" aria-controls="panel-week">1. Informe semanal</button>
    <button class="tab" id="tab-history" role="tab" aria-selected="false" aria-controls="panel-history">2. Histórico y recurrencias</button>
  </nav>
  <main>
    <section class="panel" id="panel-week" role="tabpanel" aria-labelledby="tab-week">
      <div class="meta">
        <div class="box"><div class="label">Semana</div><div class="value">34</div><div class="sub">Año 2026</div></div>
        <div class="box"><div class="label">Período</div><div class="value" style="font-size:18px">17/08–23/08</div><div class="sub">7 días completos</div></div>
        <div class="box"><div class="label">Avisos con detención</div><div class="value">{len(stopped)}</div><div class="sub">de {total_events} avisos analizados</div></div>
        <div class="box"><div class="label">Horas de detención</div><div class="value">{fmt_num(total_stops)} h</div><div class="sub">Suma de duraciones con Parada = X</div></div>
      </div>

      <h2>Disponibilidad consolidada</h2>
      <div class="kpis">
        <div class="box"><div class="label">Disponibilidad global</div><div class="value">{fmt_pct(data['global']['disponibilidad'])}</div><div class="sub">1.868,00 h disponibles; 61,86 h de parada</div></div>
        <div class="box"><div class="label">Horas de mantenimiento</div><div class="value">{fmt_num(data['global']['mantenimiento'])} h</div><div class="sub">12 puentes; base calendario global de 2.016 h</div></div>
        <div class="box"><div class="label">Mayor impacto</div><div class="value">P‑MG22</div><div class="sub">22,52 h de parada; {fmt_pct(impact['disponibilidad'])}</div></div>
        <div class="box"><div class="label">Vinculación documental</div><div class="value">{linked_stops}/{len(stopped)}</div><div class="sub">detenciones con notificación vinculable</div></div>
      </div>
      <div class="notice">Las disponibilidades de sala, serie y global se calcularon agregando primero horas calendario, mantenimiento y parada. No se usaron promedios de disponibilidades individuales.</div>

      <div class="tables-two">
        <div><h3>Por serie</h3><div class="table-wrap"><table><thead><tr><th>Serie</th><th class="num">Calendario h</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Parada h</th><th class="num">Disponibilidad</th></tr></thead><tbody>{aggregate_rows(data['series'])}</tbody></table></div></div>
        <div><h3>Por sala</h3><div class="table-wrap"><table><thead><tr><th>Sala</th><th class="num">Calendario h</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Parada h</th><th class="num">Disponibilidad</th></tr></thead><tbody>{aggregate_rows(data['salas'])}</tbody></table></div></div>
      </div>

      <h2>Disponibilidad por puente</h2>
      <div class="table-wrap"><table><thead><tr><th>Equipo</th><th>Sala</th><th>Serie</th><th class="num">Calendario h</th><th class="num">Mantenimiento h</th><th class="num">Disponible h</th><th class="num">Detenciones</th><th class="num">Parada h</th><th class="num">Disponibilidad</th><th>Observaciones de fallas</th></tr></thead><tbody>{''.join(bridge_rows)}</tbody></table></div>

      <h2>Hallazgos que requieren análisis humano</h2>
      <div class="notice risk"><strong>P‑MG22 requiere prioridad.</strong> Registró 22,52 h de parada, equivalentes al {fmt_num(impact['paradas']/total_stops*100)} % de las horas de detención de la semana. El aviso 800901556 aporta 21,07 h por “No funciona el diana”.</div>
      <ul class="actions">
        <li>La Sala 2 acumuló {fmt_num(impact_room['paradas'])} h de parada y una disponibilidad de {fmt_pct(impact_room['disponibilidad'])}; concentró {fmt_num(impact_room['paradas']/total_stops*100)} % de las horas de detención.</li>
        <li>P‑MG33 registró 16,24 h de parada. El aviso 800900542 aporta 10,55 h por “cilindro almeja roto(ROT)” y documenta el cambio del cilindro.</li>
        <li>P‑MG33 presenta dos detenciones vinculadas con la balanza y P‑MG41 una adicional. La similitud del subsistema no demuestra una causa compartida.</li>
        <li>P‑MG12 y P‑MG23 registran el mismo texto de notificación, “Reset de ATV: condensador precarga”, para fallas de descenso del aparejo de 15 TN. Debe confirmarse el modelo del variador y revisarse el historial antes de asociar las causas.</li>
      </ul>

      <h2>Detenciones y trabajos vinculados</h2>
      <p class="muted">Ordenado por equipo. Se conserva la descripción original del aviso y el texto original de cada notificación.</p>
      <div class="table-wrap"><table><thead><tr><th>Equipo</th><th>Aviso</th><th>Orden</th><th>Inicio</th><th class="num">Parada h</th><th>Categoría propuesta</th><th>Cómo falló</th><th>Causa documentada</th><th>Qué se hizo</th><th>Requiere acción</th></tr></thead><tbody>{''.join(failure_rows)}</tbody></table></div>

      <h2>Controles de calidad de datos</h2>
      <div class="notice"><strong>Sin observaciones bloqueantes:</strong> las 33 detenciones tienen duración numérica positiva y notificación vinculable del mismo equipo. No se detectaron horas de mantenimiento negativas, duplicados exactos, paradas superpuestas ni coincidencias temporales entre parada y mantenimiento programado.</div>
      <p>Se excluyeron 11 registros de tareas fuera del alcance, correspondientes a salas, zonas u otros equipos: SALA 3 1°, P‑RTP1, SALA 4 1°, P‑BAA3, SALA 2 1°, ZONA MANT., SALA 3 3°, SALA 4 3°, P‑EEE1 y P‑PC04. No se usó su información en ningún cálculo.</p>

      <h2>Criterios técnicos externos</h2>
      <ul class="source-list">
        <li>OSHA 1910.179 exige inspeccionar mecanismos funcionales, frenos, elementos mecánicos y aparatos eléctricos, y mantener un programa preventivo basado en las recomendaciones del fabricante. Esto respalda priorizar la revisión de traslación, izaje, frenos, controles y contactos, sin reemplazar los procedimientos internos. <a href="https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.179" target="_blank" rel="noopener">Fuente OSHA</a>.</li>
        <li>Schneider Electric indica que una falla del condensador de precarga en ATV600/900 puede relacionarse con tensión de red inestable o vida agotada de los condensadores del enlace de continua, y recomienda comprobar tensión, cableado interno y puesta a tierra. El modelo instalado debe confirmarse antes de aplicar esta referencia. <a href="https://www.se.com/us/en/faqs/FA371871/" target="_blank" rel="noopener">Fuente Schneider Electric</a>.</li>
        <li>Las referencias externas no permiten interpretar qué componente denomina “diana” la instalación ni atribuir causa raíz a las fallas de balanza, ECL o picador. Esos puntos permanecen sujetos a planos, manuales del fabricante y validación del personal.</li>
      </ul>
    </section>

    <section class="panel" id="panel-history" role="tabpanel" aria-labelledby="tab-history" hidden>
      <h2>Histórico y recurrencias</h2>
      <div class="notice warning"><strong>Semanas analizadas: 1.</strong> Solo se procesó la semana 34/2026. No se calcularon ni utilizaron semanas anteriores para comparar valores, calcular variaciones o establecer tendencias. Los grupos siguientes son coincidencias dentro de la semana actual y requieren validación humana.</div>
      <div class="filters" aria-label="Filtros históricos">
        <label>Semana<select id="filter-week"><option value="34">34/2026</option></select></label>
        <label>Puente<select id="filter-bridge"><option value="">Todos</option>{''.join(f'<option>{esc(r["equipo"])}</option>' for r in data['puentes'])}</select></label>
        <label>Serie<select id="filter-series"><option value="">Todas</option><option>A</option><option>B</option></select></label>
        <label>Sala<select id="filter-room"><option value="">Todas</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
        <label>Categoría de falla<select id="filter-category"><option value="">Todas</option>{''.join(f'<option>{esc(c)}</option>' for c in categories)}</select></label>
      </div>
      <p class="muted" id="filter-note">La categoría filtra horas de parada y detenciones; la disponibilidad conserva todas las paradas de los puentes seleccionados.</p>
      <div class="charts">
        <div class="chart"><h3>Disponibilidad</h3><svg id="chart-availability" role="img" aria-label="Disponibilidad filtrada por semana"></svg></div>
        <div class="chart"><h3>Horas de parada</h3><svg id="chart-hours" role="img" aria-label="Horas de parada filtradas por semana"></svg></div>
        <div class="chart"><h3>Cantidad de detenciones</h3><svg id="chart-count" role="img" aria-label="Cantidad de detenciones filtradas por semana"></svg></div>
      </div>

      <h2>Valores calculados y almacenados</h2>
      <div class="table-wrap"><table id="history-table"><thead><tr><th>Semana</th><th>Período</th><th>Equipo</th><th>Sala</th><th>Serie</th><th class="num">Mantenimiento h</th><th class="num">Parada h</th><th class="num">Detenciones</th><th class="num">Disponibilidad</th><th>Interpretación</th><th>Revisión humana</th></tr></thead><tbody>{''.join(f'<tr data-bridge="{r["equipo"]}" data-series="{r["serie"]}" data-room="{r["sala"]}"><td>34/2026</td><td>17/08/2026–23/08/2026</td><td class="tag">{r["equipo"]}</td><td>{r["sala"]}</td><td>{r["serie"]}</td><td class="num">{fmt_num(r["mantenimiento"])}</td><td class="num">{fmt_num(r["paradas"])}</td><td class="num">{r["detenciones"]}</td><td class="num strong">{fmt_pct(r["disponibilidad"])}</td><td>Resultado semanal; no existe base previa para variación.</td><td>Sí, antes de interpretar como tendencia.</td></tr>' for r in data['puentes'])}</tbody></table></div>

      <h2>Recurrencias potenciales dentro de la semana</h2>
      <div class="table-wrap"><table id="recurrence-table"><thead><tr><th>Categoría propuesta</th><th>Fuente de repetición</th><th>Descripciones originales</th><th>Puentes afectados</th><th>Semanas</th><th class="num">Fallas</th><th>Causas documentadas</th><th>Intervenciones realizadas</th><th>Confianza de asociación</th><th>Justificación</th><th>Necesidad de revisión humana</th></tr></thead><tbody>{''.join(recurrence_rows)}</tbody></table></div>
    </section>
  </main>
  <footer>Reporte generado a partir de los tres archivos de la semana 34. Fórmula por puente: (168 h − mantenimiento − parada) / (168 h − mantenimiento) × 100. No contiene proyecciones ni comparaciones con semanas anteriores.</footer>
</div>
<script>
const reportData = {data_js};
const tabs = [...document.querySelectorAll('.tab')];
tabs.forEach(tab => tab.addEventListener('click', () => {{
  tabs.forEach(t => t.setAttribute('aria-selected', String(t === tab)));
  document.querySelectorAll('.panel').forEach(p => p.hidden = p.id !== tab.getAttribute('aria-controls'));
  if (tab.id === 'tab-history') updateHistory();
}}));
const q = id => document.getElementById(id);
const filters = ['filter-bridge','filter-series','filter-room','filter-category'].map(q);
filters.forEach(el => el.addEventListener('change', updateHistory));
function chosenBridges() {{
  const bridge=q('filter-bridge').value, series=q('filter-series').value, room=q('filter-room').value;
  return reportData.bridges.filter(r => (!bridge||r.equipo===bridge)&&(!series||r.serie===series)&&(!room||String(r.sala)===room));
}}
function fmt(v, digits=2) {{ return v.toLocaleString('es-AR',{{minimumFractionDigits:digits,maximumFractionDigits:digits}}); }}
function drawBar(id, value, max, suffix) {{
  const svg=q(id), w=360, h=220, left=52, right=18, top=24, bottom=44, chartH=h-top-bottom;
  const safe=Math.max(0,Math.min(value,max)), barH=max ? chartH*safe/max : 0, y=top+chartH-barH;
  svg.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);
  svg.innerHTML=`<line class="axis" x1="${{left}}" y1="${{top+chartH}}" x2="${{w-right}}" y2="${{top+chartH}}"/><line class="axis" x1="${{left}}" y1="${{top}}" x2="${{left}}" y2="${{top+chartH}}"/><text class="chart-label" x="${{left-7}}" y="${{top+4}}" text-anchor="end">${{fmt(max, max===100?0:1)}}</text><text class="chart-label" x="${{left-7}}" y="${{top+chartH+4}}" text-anchor="end">0</text><rect class="bar" x="145" y="${{y}}" width="100" height="${{barH}}"/><text class="chart-value" x="195" y="${{Math.max(16,y-7)}}" text-anchor="middle">${{fmt(value)}} ${{suffix}}</text><text class="chart-label" x="195" y="${{h-16}}" text-anchor="middle">Semana 34</text>`;
}}
function updateHistory() {{
  const bridges=chosenBridges(), ids=new Set(bridges.map(r=>r.equipo)), category=q('filter-category').value;
  const events=reportData.events.filter(e=>ids.has(e.equipo)&&(!category||e.categoria===category));
  const available=bridges.reduce((s,r)=>s+r.tiempo_disponible,0), allStops=bridges.reduce((s,r)=>s+r.paradas,0);
  const availability=available ? (available-allStops)/available*100 : 0;
  const hours=events.reduce((s,e)=>s+e.duracion,0), count=events.length;
  drawBar('chart-availability',availability,100,'%'); drawBar('chart-hours',hours,Math.max(110,hours*1.12),'h'); drawBar('chart-count',count,Math.max(42,count*1.12),'');
  document.querySelectorAll('#history-table tbody tr').forEach(tr=>tr.hidden=!ids.has(tr.dataset.bridge));
  document.querySelectorAll('#recurrence-table tbody tr').forEach(tr=>{{
    const matchesBridge=!q('filter-bridge').value||tr.dataset.bridge.split('|').includes(q('filter-bridge').value);
    const matchesSeries=!q('filter-series').value||tr.dataset.series.split('|').includes(q('filter-series').value);
    const matchesRoom=!q('filter-room').value||tr.dataset.room.split('|').includes(q('filter-room').value);
    const matchesCategory=!category||tr.dataset.category===category;
    tr.hidden=!(matchesBridge&&matchesSeries&&matchesRoom&&matchesCategory);
  }});
}}
updateHistory();
</script>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(document, encoding="utf-8")
    print(OUT_PATH)


if __name__ == "__main__":
    main()
