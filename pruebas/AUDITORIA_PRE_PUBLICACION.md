# Auditoría de privacidad previa a GitHub

**Fecha:** 11/09/2026  
**Alcance:** archivos preparados en el índice de Git para el repositorio público.

## Resultado

La revisión no encontró claves API, tokens de GitHub, claves privadas, correos electrónicos, teléfonos, DNI, legajos ni nombres completos de empleados en los datos y salidas preparados para publicación.

Las apariciones de la palabra `operario` describen un rol genérico y no incluyen identidad. Los números de siete a nueve dígitos detectados en las corridas corresponden a avisos y órdenes técnicas, campos expresamente permitidos por el contrato del agente.

## Exclusiones verificadas

Git excluye mediante `.gitignore`:

- `runtime/` y sus bases/respaldos;
- `data/` y bases SQLite;
- libros `.xlsx`, `.xls` y `.xlsm`;
- archivos `.zip`;
- `.env` y `.env.local`;
- cachés y bytecode de Python.

Los dos Excel generados durante el desarrollo histórico permanecen localmente pero no se incorporan al repositorio. `.env.example` sí se publica porque contiene únicamente marcadores de posición y ninguna credencial real.

## Evidencia oficial

Las ocho corridas oficiales conservan manifiestos con nombres de archivo y SHA-256, prompts, validaciones, JSON derivados, uso de la API, metadatos e informes HTML. No contienen los Excel fuente ni la base histórica real.

## Riesgo residual declarado

Los reportes incluyen códigos de equipo, números técnicos de aviso/orden y descripciones reales de fallas. No son datos personales según el contrato aplicado, pero sí constituyen información operativa. Su publicación se realiza exclusivamente como evidencia académica autorizada. Una implementación productiva debe mantener los reportes detrás de autenticación y no utilizar un repositorio público como almacenamiento operativo.

## Conclusión

La selección está apta para publicación desde el punto de vista de secretos y datos personales. La revisión es preventiva y no garantiza detección absoluta; cualquier archivo agregado en el futuro debe volver a auditarse antes de un commit público.

## Revisión incremental de la ronda 2

**Fecha:** 12/09/2026  
**Alcance:** `pruebas/comparacion_modelos_real/ronda_02/` y documentos actualizados para el cierre de AE-03.

Se verificaron los seis resultados de API, manifiesto, controles objetivos, planillas de revisión humana normalizada y conclusión. No se detectaron claves con formato OpenAI ni credenciales. La evidencia conserva identificadores técnicos, textos de falla, `response_id`, tokens y costos, pero no los Excel fuente ni valores de `OPENAI_API_KEY`.

La revisión humana se atribuye al rol responsable y no incluye el nombre de una persona. Los archivos quedan aptos para incorporarse como evidencia académica, manteniendo el riesgo residual operativo ya declarado.
