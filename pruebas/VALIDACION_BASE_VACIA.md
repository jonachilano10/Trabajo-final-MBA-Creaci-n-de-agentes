# Validación del entorno de entrega vacío

**Fecha:** 9 de septiembre de 2026  
**Resultado:** aprobado

## Objetivo

Preparar una instancia independiente para ejecutar las corridas finales desde cero sin borrar ni alterar el historial utilizado durante el desarrollo.

## Entorno nuevo

- Directorio: `runtime/entrega_final`.
- Base: `runtime/entrega_final/data/historico.sqlite3`
- Integridad SQLite: `ok`
- Semanas almacenadas: `0`
- SHA-256 inicial: `2ACB2CF3AB124AB9C6D489C7A398DE83B8F25FA75CB21FEFC4B74D4F0524C7F9`
- Tablas creadas: `weeks`, `equipment_week`, `aggregate_week`, `maintenance_events`, `failure_events`, `validation_issues`, `llm_findings` y `llm_runs`.

La carpeta contiene directorios separados para `data`, `salidas` y `corridas`. Está excluida de Git mediante la regla `runtime/`.

## Comprobación del historial existente

- Base conservada: `data/historico.sqlite3`
- Semanas antes y después de preparar el entorno nuevo: `3`
- SHA-256 antes: `F13FA4374A4C0BAD9A8279893870C6E6EA5028A59621B9511EB50C002170A98B`
- SHA-256 después: `F13FA4374A4C0BAD9A8279893870C6E6EA5028A59621B9511EB50C002170A98B`

La coincidencia de las huellas confirma que la base histórica no fue modificada.

## Inicio de la aplicación

Ejecutar `iniciar_entrega.bat`. El archivo define `AGENT_DATA_DIR` antes de iniciar la web, por lo que toda nueva carga se dirige al entorno separado.

El iniciador no elimina ni reinicia la base. Después de cargar la primera semana, las ejecuciones siguientes continúan acumulando historial. Para otra prueba completamente nueva debe prepararse un directorio diferente o respaldar y retirar deliberadamente el entorno anterior.
