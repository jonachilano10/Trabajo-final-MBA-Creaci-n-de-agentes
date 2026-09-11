# Corridas del agente

Esta carpeta contiene la evidencia reconstruible del proyecto. Las ocho carpetas `corrida_2026-*` corresponden a la secuencia oficial ejecutada desde una base vacía. `desarrollo_historico/` conserva, sin reescribir, las iteraciones anteriores que permitieron llegar a la versión final.

## Corridas oficiales

| Semana | Período | Disponibilidad | Parada | Detenciones | LLM |
|---:|---|---:|---:|---:|---|
| 29 | 13/07/2026–19/07/2026 | 98,28 % | 32,23 h | 28 | Completado |
| 30 | 20/07/2026–26/07/2026 | 98,57 % | 26,37 h | 21 | Completado |
| 31 | 27/07/2026–02/08/2026 | 97,89 % | 39,40 h | 39 | Completado |
| 32 | 03/08/2026–09/08/2026 | 97,62 % | 44,19 h | 32 | Completado |
| 33 | 10/08/2026–16/08/2026 | 94,40 % | 106,03 h | 40 | Completado |
| 34 | 17/08/2026–23/08/2026 | 96,69 % | 61,86 h | 33 | Completado |
| 35 | 24/08/2026–30/08/2026 | 97,89 % | 39,35 h | 30 | Completado |
| 36 | 31/08/2026–06/09/2026 | 95,48 % | 83,36 h | 42 | Completado |

Cada corrida oficial contiene:

```text
corrida_YYYY-MM-DD_semana_NN/
  README.md
  METADATA.json
  entrada/
    ARCHIVOS.md
  prompts/
    SYSTEM_PROMPT.txt
    USER_PROMPT.txt
    USER_PROMPT_TEMPLATE.md
    CONTRATO_FUNCIONAL_AGENTE.md
  salida/
    resultados.json
    contexto_llm.json
    hallazgos_llm.json
    ejecuciones_llm.json
    Reporte_Disponibilidad_SemanaNN.html
  validacion/
    VALIDACION.md
```

`METADATA.json` identifica período, modelo, nivel de razonamiento, estado del LLM y huellas SHA-256. `ejecuciones_llm.json` registra tokens y costo. Los JSON y el HTML permiten revisar tanto los cálculos determinísticos como la interpretación preliminar del LLM.

## Protección de las entradas

Los Excel originales no se publican porque contienen información operativa y podrían incorporar información personal. `entrada/ARCHIVOS.md` conserva el nombre y la huella SHA-256 de cada fuente, sin copiar su contenido. Los cálculos derivados y el contexto enviado al LLM se conservan en formato estructurado.

Los archivos deliberadamente confidenciales usados para probar el rechazo de privacidad permanecen fuera del repositorio público. La evidencia de esa prueba está documentada en `../pruebas/PRUEBA_PRIVACIDAD_SEMANAS_31_Y_36.md`.

## Desarrollo histórico

`desarrollo_historico/` contiene cinco iteraciones de la semana 33, una corrida provisional de la semana 34 y una corrida histórica de la semana 35. Muestran errores, correcciones y cambios de alcance; no se presentan como períodos independientes ni se completaron retroactivamente con información que no existía cuando fueron ejecutadas.
