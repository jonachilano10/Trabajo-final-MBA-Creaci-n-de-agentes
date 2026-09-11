# Matriz de cumplimiento final

Estado verificado el 11/09/2026.

| Requisito de la consigna | Evidencia principal | Estado |
|---|---|---|
| Sistema completo | `agente_mantenimiento/`, web, SQLite, Structured Outputs y reportes HTML | Cumplido |
| Objetivo y contrato con seis piezas | `prompts/system_prompt.md`, `prompts/user_prompt.md` y `prompts/contrato_funcional_agente.md` | Cumplido |
| Herramientas reales | Lectura de tres Excel, base SQLite y Responses API | Cumplido |
| Salida estructurada | SQLite y JSON validados; HTML generado desde datos calculados por Python | Cumplido |
| Supervisión L0–L4 | `GOBIERNO_Y_RIESGO.md`; el ingeniero revisa y firma antes de actuar | Cumplido |
| Al menos tres corridas reales | `corridas/`: ocho semanas oficiales, 29–36/2026 | Cumplido |
| Corridas reconstruibles | Entrada identificada por SHA-256, prompts exactos, validación, JSON, uso del LLM, metadatos y HTML | Cumplido |
| Formato estricto | `README.md`, `prompts/`, `corridas/` y `DECISIONES.md` | Cumplido |
| Historia del proceso | `DECISIONES.md` y `corridas/desarrollo_historico/` | Cumplido |
| Análisis económico | `ANALISIS_ECONOMICO.md` y `ejecuciones_llm.json` de cada corrida | Cumplido con consumo real |
| Gobierno y riesgo | `GOBIERNO_Y_RIESGO.md` y cuestionario de respaldo | Cumplido |
| Control de privacidad | Filtro previo al cálculo/LLM y prueba negativa documentada | Cumplido |
| Límite de contexto | Semana actual más un máximo de seis anteriores | Cumplido y probado |
| Pruebas automatizadas | `tests/`: 13 pruebas aprobadas el 11/09/2026 | Cumplido |

## Pendiente externo al funcionamiento

La carpeta está preparada para la auditoría de privacidad y la publicación en un repositorio GitHub público. La publicación, configuración del proveedor y dominio forman parte del paso siguiente y no se presentan como ya realizadas.
