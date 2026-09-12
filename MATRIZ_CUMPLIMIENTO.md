# Matriz de cumplimiento y respuesta a la evaluación

Estado revisado el 11/09/2026 después de la devolución externa de 85/100. Esta matriz distingue evidencia existente, corrección aplicada y pendientes humanos; no declara completa una prueba que todavía no se ejecutó.

| Criterio | Evidencia verificable | Estado |
|---|---|---|
| SC-01 — Contrato de prompts | `prompts/system_prompt.md`, `prompts/user_prompt.md` | Cumplido 8/8 en evaluación |
| SC-02 — Herramienta/conector real | `HERRAMIENTAS_Y_CONECTORES.md`; `agente_mantenimiento/llm_openai.py`; trazas `ejecuciones_llm.json`; reproducción sintética | Corrección implementada; listo para reevaluar |
| SC-03 — Salida estructurada | JSON Schema estricto, `validate_llm_payload`, `hallazgos_llm.json` | Cumplido 7/7 en evaluación |
| SC-04 — Supervisión | `GOBIERNO_Y_RIESGO.md` y aviso obligatorio en reportes | Cumplido 7/7 en evaluación |
| PD-01 — Iteraciones trazables | `DECISIONES.md`, `corridas/desarrollo_historico/` | Cumplido |
| PD-02 — Fallas preservadas | Corridas 1–6 y pruebas negativas | Cumplido |
| PD-03 — Decisiones con evidencia | `DECISIONES.md` enlaza problema, cambio y prueba | Cumplido |
| FR-01 — Estructura mínima | README, prompts y decisiones en raíz | Cumplido 5/5 en evaluación |
| FR-02 — Tres corridas | Ocho corridas oficiales, semanas 29–36 | Cumplido 5/5 en evaluación |
| FR-03 — Reconstrucción exacta | `REPRODUCIBILIDAD.md`, `VERSION`, `requirements-lock.txt`, `scripts/reproducir_demo.py`, evidencia generada y nuevo manifiesto automático | Corrección implementada; listo para reevaluar |
| AE-01 — Consumo real | `CONSUMO_REAL_CORRIDAS.csv`, trazas con tokens y costo | Cumplido |
| AE-02 — Proyección económica | `ANALISIS_ECONOMICO.md` | Cumplido |
| AE-03 — Configuración costo-eficiente | Seis llamadas reales, costos, control objetivo y planilla reducida de revisión | Pendiente únicamente de revisión humana |
| Gobierno y riesgo | `GOBIERNO_Y_RIESGO.md`, privacidad y autenticación | Cumplido |

## Evidencia nueva para SC-02

La herramienta se identifica por nombre, endpoint, código, permisos, credencial, datos intercambiados y restricciones. Las trazas reales aportan `response_id`, tokens, costo y salida. La reproducción sin red verifica el cuerpo estructurado y la validación sin pagar una llamada en cada prueba.

## Evidencia nueva para FR-03

La versión 1.1.0 registra versión, commit cuando está disponible, hash exacto del código, entorno, dependencias, entrada web y hashes de artefactos. Una corrida sintética completa permite reconstruir el flujo desde una base vacía sin publicar datos operativos. Las ocho corridas anteriores mantienen declarada la ausencia de un commit contemporáneo.

## Pendiente controlado para AE-03

Las seis llamadas reales se completaron. Nano y Mini tuvieron un error objetivo de alcance cada uno; GPT-5.4 no. Falta revisar y aprobar técnicamente los 21 hallazgos del único candidato que superó esa barrera. La clave no se guardó en el repositorio.

## Publicación

El código y la evidencia académica están en el repositorio `jonachilano10/Trabajo-final-MBA-Creaci-n-de-agentes`. El despliegue público continúa separado de la demostración académica y requiere backend persistente, HTTPS, secretos y respaldo.
