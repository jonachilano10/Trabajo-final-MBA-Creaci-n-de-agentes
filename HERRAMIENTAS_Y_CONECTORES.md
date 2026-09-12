# Herramientas y conectores reales

Este documento concentra la evidencia operativa del criterio **SC-02**. El agente no simula integraciones: procesa libros Excel, persiste resultados en SQLite y utiliza la OpenAI Responses API para la interpretación semántica. Las ocho corridas oficiales conservan trazas reales de la API; la reproducción sintética permite verificar localmente el circuito sin exponer datos de planta.

## 1. Conector OpenAI Responses API

| Campo | Implementación verificable |
|---|---|
| Herramienta | OpenAI Responses API mediante HTTPS |
| Código | `agente_mantenimiento/llm_openai.py`, funciones `_call_responses_api` e `interpret_week_with_openai` |
| Autenticación | Secreto `OPENAI_API_KEY` leído exclusivamente desde el entorno |
| Permiso efectivo | Una solicitud saliente `POST` a `https://api.openai.com/v1/responses` |
| Datos enviados | System prompt y hechos textuales ya filtrados de la semana actual y hasta seis semanas anteriores |
| Datos excluidos | Excel originales, clave, base SQLite, nombres personales y métricas que el LLM no puede modificar |
| Persistencia del proveedor | `store: false` |
| Contrato de salida | JSON Schema estricto con máximo 12 hallazgos |
| Control posterior | `validate_llm_payload` rechaza campos extra, métricas, avisos inexistentes, textos vacíos y relaciones cuyo tipo no coincide con los puentes citados |
| Acciones prohibidas | No modifica Excel, cálculos, SQLite fuera de sus hallazgos, SAP ni equipos de planta |

### Traza real preservada

Cada corrida oficial contiene:

- `salida/ejecuciones_llm.json`: modelo, nivel, `response_id`, tokens y costo real;
- `salida/contexto_llm.json`: entrada estructurada enviada;
- `salida/hallazgos_llm.json`: salida estructurada validada;
- `salida/solicitud_llm.json`: endpoint, configuración y huellas del prompt, contexto, esquema y salida;
- `prompts/SYSTEM_PROMPT.txt`: instrucciones exactas aplicadas.

Ejemplo: `corridas/corrida_2026-09-09_semana_29/`. El `response_id` demuestra una llamada real; la clave nunca se archiva.

## 2. Lectura de Excel con OpenPyXL

| Campo | Implementación verificable |
|---|---|
| Herramienta | OpenPyXL 3.1.5 |
| Código | `agente_mantenimiento/privacy.py` y `agente_mantenimiento/analysis.py` |
| Permiso | Lectura local de los tres archivos seleccionados por el usuario |
| Modo | `read_only=True`, `data_only=True` |
| Escritura sobre la fuente | Ninguna |
| Controles previos | Extensión, tamaño, estructura y barrido de privacidad de todas las hojas y valores |
| Evidencia | Prueba sintética y pruebas automatizadas de privacidad y procesamiento web |

Los archivos subidos se copian a un directorio temporal, se cierran y se eliminan. Sólo se conservan nombres, SHA-256 y resultados estructurados.

## 3. Persistencia SQLite

| Campo | Implementación verificable |
|---|---|
| Herramienta | SQLite incluida en Python |
| Código | `agente_mantenimiento/database.py` |
| Permisos | Lectura y escritura únicamente sobre la base configurada por `AGENT_DATA_DIR` o `--db` |
| Información | Semanas, métricas, eventos, validaciones, hallazgos y consumo del LLM |
| Control de duplicados | Restricción única año-semana y excepción explícita |
| Acceso externo | Ninguno; no abre puertos ni comparte la base |
| Evidencia | Ocho semanas oficiales y reproducción desde una base temporal vacía |

## Pruebas reproducibles

Prueba completa y sin red:

```powershell
python scripts/reproducir_demo.py
```

Pruebas automáticas:

```powershell
python -m unittest discover -s tests -v
```

La primera prueba genera tres Excel sintéticos, ejecuta privacidad, cálculo, SQLite, contrato LLM con transporte controlado y reporte. La segunda comprueba además el cuerpo enviado al conector, el esquema estricto, `store: false`, costos, duplicados y seguridad web. La llamada real queda probada por las trazas archivadas; el transporte controlado evita gastar tokens en cada verificación técnica.

## Permisos resumidos

```text
Usuario selecciona tres Excel
        │ lectura temporal
        ▼
OpenPyXL ──sin escritura sobre originales──► Python
                                                │ lectura/escritura local
                                                ▼
                                             SQLite
                                                │ sólo hechos filtrados
                                                ▼
OpenAI Responses API ──JSON preliminar──► validación Python
```

El alcance respeta mínimo privilegio: el único permiso remoto es invocar la API con una clave configurada por el operador.
