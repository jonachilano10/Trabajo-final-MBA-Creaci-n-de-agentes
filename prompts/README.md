# Prompts y contrato funcional

## Archivos canónicos

- `system_prompt.md`: system prompt exacto que la aplicación envía al LLM mediante el campo `instructions` de la API. Contiene las seis piezas exigidas: rol, contexto, tarea, fuentes y restricciones, formato de salida y ejemplos.
- `user_prompt.md`: plantilla de la solicitud semanal. Cada corrida archiva una versión completada con semana, período y nombres de los tres archivos utilizados.
- `contrato_funcional_agente.md`: especificación extensa del sistema completo. Documenta privacidad, cálculos, equipos, disponibilidad, historial y diseño del HTML que Python implementa de forma determinística. No se envía al LLM.

`SYSTEM_PROMPT.txt`, ubicado en la raíz por compatibilidad con las primeras iteraciones del trabajo, es una copia sincronizada del system prompt canónico. El programa siempre carga la versión de `prompts/system_prompt.md`.

## División de responsabilidades

Python valida los Excel, rechaza información confidencial, calcula métricas, consulta SQLite, limita el historial, prepara el JSON y valida la respuesta. El LLM recibe `system_prompt.md` y ese JSON para relacionar fallas y redactar hallazgos preliminares. No recibe autorización para calcular o modificar valores.

Esta separación mantiene un único system prompt real y auditable, evita instrucciones ocultas en el código y no incorpora al consumo del LLM ejemplos extensos de cálculos que ya ejecuta Python.

Cada nueva corrida web archiva copias exactas del system prompt, del contrato funcional, del user prompt completado y de su plantilla. También conserva modelo, nivel, contexto, hallazgos, tokens y costos cuando la API responde.
