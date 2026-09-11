# Arquitectura y evolución del agente

## Arquitectura final

```text
Página web / CLI
       │ tres Excel + período
       ▼
Privacidad y validación estructural
       │ rechazo temprano o lote válido
       ▼
Cálculo determinístico en Python
       │ métricas y eventos estructurados
       ▼
SQLite ───────────────► gráficos históricos completos
       │ semana actual + máximo 6 anteriores
       ▼
OpenAI Responses API
       │ JSON Schema estricto
       ▼
Validación Python ────► interpretación preliminar
       │
       ▼
HTML + revisión y firma humana
```

## Evolución trazable

```text
Iteración 1: respuesta textual inicial
      │ faltaban estructura y trazabilidad
      ▼
Iteraciones 2–6: cálculo semanal y reportes HTML
      │ se corrigieron series, salas y recálculo desde fuentes
      ▼
Semana 35: Python + SQLite + salida LLM estructurada
      │ faltaban historial web completo y controles productivos
      ▼
Versión final inicial: semanas 29–36, privacidad, web e historial
      │ evaluación externa 85/100 detectó evidencia dispersa
      ▼
Versión 1.1.0: conectores explícitos, reproducción y benchmark auditable
```

Las fallas y decisiones de cada etapa se conservan en `corridas/desarrollo_historico/` y `DECISIONES.md`. Las mejoras de la versión 1.1.0 no reemplazan las corridas anteriores: agregan evidencia verificable y controles para las siguientes.
