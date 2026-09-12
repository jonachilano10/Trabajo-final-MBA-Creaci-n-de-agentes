# Matriz de cumplimiento y respuesta a la evaluación

Estado revisado el 12/09/2026 después de completar la segunda ronda del benchmark y su revisión humana. Esta matriz distingue la evidencia original, las correcciones y el cierre verificable.

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
| AE-03 — Configuración costo-eficiente | Dos rondas reales; `ronda_02/resultados_api.json`, `revision_humana_normalizada.csv` y `CONCLUSION_EVALUACION.json` | Cumplido: GPT-5.4 Mini / `medium` seleccionado |
| Gobierno y riesgo | `GOBIERNO_Y_RIESGO.md`, privacidad y autenticación | Cumplido |

## Evidencia nueva para SC-02

La herramienta se identifica por nombre, endpoint, código, permisos, credencial, datos intercambiados y restricciones. Las trazas reales aportan `response_id`, tokens, costo y salida. La reproducción sin red verifica el cuerpo estructurado y la validación sin pagar una llamada en cada prueba.

## Evidencia nueva para FR-03

La versión 1.1.0 registra versión, commit cuando está disponible, hash exacto del código, entorno, dependencias, entrada web y hashes de artefactos. Una corrida sintética completa permite reconstruir el flujo desde una base vacía sin publicar datos operativos. Las ocho corridas anteriores mantienen declarada la ausencia de un commit contemporáneo.

## Cierre verificable de AE-03

La ronda 1 no aprobó y se preservó sin reducir el umbral. Después del prompt 1.3.0, la ronda 2 completó seis llamadas y 33 revisiones humanas. GPT-5.4 Mini / `medium` fue el único modelo que alcanzó 100 % de corrección, 2,00/2 de utilidad y cero afirmaciones no respaldadas. Costó US$ 0,0724725 para dos semanas, frente a US$ 0,2393700 de GPT-5.4. La selección no depende de una estimación: puede reconstruirse desde los JSON y CSV archivados. La clave nunca se guardó en el repositorio.

## Publicación

El código y la evidencia académica están en el repositorio `jonachilano10/Trabajo-final-MBA-Creaci-n-de-agentes`. El despliegue público continúa separado de la demostración académica y requiere backend persistente, HTTPS, secretos y respaldo.
