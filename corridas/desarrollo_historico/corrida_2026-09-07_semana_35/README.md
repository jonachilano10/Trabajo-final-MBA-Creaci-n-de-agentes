# Corrida del 07/09/2026 - Semana 35

## Clasificación

Corrida real incorporada al historial SQLite.

## Ejecución

- Período analizado: 24/08/2026 al 30/08/2026.
- Semana y año: 35/2026.
- Fecha de procesamiento registrada por SQLite: 07/09/2026 19:49:28.
- Objetivo: calcular disponibilidad semanal y actualizar el historial.
- Base de cálculo: 168 h por puente, 504 h por sala, 1.008 h por serie y 2.016 h globales.
- Modelo conversacional: Codex; versión exacta, tokens y costo no expuestos por el entorno.

## Entradas

Consultar `entrada/ARCHIVOS.md`. Los Excel originales no se duplicaron ni modificaron porque contienen información operativa. El manifiesto conserva nombre, origen relativo y SHA-256.

## Salidas

- `salida/Reporte_Disponibilidad_Semana35.html`: copia del reporte generado desde la base histórica.
- `salida/resultados.json`: valores estructurados principales de esta semana.
- `salida/contexto_llm.json`: hechos textuales exportados desde SQLite para interpretación.
- `salida/hallazgos_llm.json`: interpretación producida por el LLM y validada antes de guardarse.
- `validacion/VALIDACION.md`: controles y observaciones detectadas.

## Prompts conservados

- `prompts/SYSTEM_PROMPT.txt`: system prompt completo y exacto utilizado como contrato funcional. SHA-256: `3834733638E7E2877B2F2EE171D6527AED87876E2E2D7751D98AF6BAAAAA80D1`.
- `prompts/USER_PROMPT.txt`: solicitud correspondiente a la semana 35.
- `prompts/CONTRATO_APLICADO.md`: resumen de las reglas aplicadas por el código determinístico.

La información estructurada completa permanece en `Trabajo final/data/historico.sqlite3`. Allí la semana 35 convive con las semanas 33 y 34 y está protegida por la clave única año-semana.

## Resultado consolidado

- Disponibilidad global: 97,88894849785407 %.
- Mantenimiento: 152,00 h.
- Tiempo disponible: 1.864,00 h.
- Horas de parada: 39,35 h.
- Detenciones: 30.

No se calcularon proyecciones ni se inventaron semanas faltantes.
