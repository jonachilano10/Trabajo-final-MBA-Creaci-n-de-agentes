# Reproducibilidad y reconstrucción de corridas

Este documento responde al criterio **FR-03** y distingue dos clases de evidencia para no atribuir retrospectivamente datos que no fueron capturados.

## Corridas oficiales 29–36

Las ocho corridas son ejecuciones reales y conservan período, nombres y SHA-256 de las fuentes, prompts, resultados de Python, contexto y hallazgos del LLM, `response_id`, tokens, costo y HTML. Los Excel originales no se publican por privacidad y seguridad operativa.

La versión/commit exactos no se capturaron contemporáneamente en esas ocho corridas. Esta limitación se declara en `pruebas/RECONSTRUCCION_CORRIDAS_HISTORICAS.md`; no se completó ese dato de manera retroactiva ni se inventó una referencia.

## Versión reproducible

A partir de la versión `1.1.0`, cada nueva corrida archiva en `METADATA.json`. La versión `1.2.0` agrega además la validación entre `relation_type` y el puente real de cada aviso:

- versión del esquema de metadatos;
- versión declarada del agente;
- commit Git, si está disponible o fue inyectado al despliegue;
- SHA-256 del código, prompts y dependencias ejecutables;
- versión de Python y dependencias;
- ruta de entrada (`web:POST /procesar`);
- modelo, razonamiento y período;
- SHA-256 de fuentes y artefactos de salida.

El hash del código permite identificar el contenido exacto incluso si Git no está instalado en el servidor. `requirements-lock.txt` fija las dependencias de la versión entregada.

## Reproducción segura desde cero

Requisitos:

```powershell
python -m pip install -r requirements-lock.txt
```

Ejecución:

```powershell
python scripts/reproducir_demo.py
```

El script:

1. crea una base SQLite vacía;
2. genera tres Excel sintéticos sin nombres, legajos ni datos personales;
3. ejecuta el control de privacidad;
4. calcula y persiste una semana;
5. valida una respuesta LLM determinística mediante el mismo contrato de producción;
6. genera el HTML;
7. compara métricas con valores esperados;
8. guarda hashes, versiones y resultados en `pruebas/evidencia_reproducibilidad/`.

No usa Internet ni consume tokens. Los Excel temporales se eliminan al finalizar. Cualquier tercero con el repositorio puede repetir la prueba sin acceder a las fuentes confidenciales.

## Resultado determinístico esperado

| Métrica | Valor esperado |
|---|---:|
| Mantenimiento | 4,00 h |
| Parada | 3,75 h |
| Detenciones | 2 |
| Disponibilidad global | 99,8136182903 % |

Las métricas, la persistencia y la validación deben coincidir exactamente. La redacción de una llamada real al LLM no es byte a byte determinística; por eso las corridas preservan la salida recibida, mientras la reproducción sin red usa una respuesta controlada.

## Ejecución real opcional

Con una clave configurada puede repetirse la interpretación real:

```powershell
$env:OPENAI_API_KEY="tu_clave"
python run_agent.py --db "ruta\historico.sqlite3" interpretar --anio 2026 --semana 36
```

La salida debe volver a cumplir el esquema y referenciar sólo avisos existentes, pero su redacción puede variar. No debe utilizarse esta variabilidad para modificar valores calculados por Python.
