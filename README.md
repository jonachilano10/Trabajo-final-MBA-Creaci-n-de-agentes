# Agente de disponibilidad de puentes grúa

Sistema agéntico para calcular la disponibilidad semanal de 12 puentes grúa, conservar historial, comparar períodos y proponer relaciones preliminares entre fallas. Python valida y calcula; el LLM sólo interpreta textos y no puede crear ni modificar métricas.

## Estado final

- Versión actual `1.3.1`, con validación cruzada, límite de ocho hallazgos, control de redundancia/utilidad y benchmark tolerante a rechazos.
- Ocho corridas oficiales completas: semanas 29 a 36 de 2026.
- Base local estructurada en SQLite con control de duplicados.
- Página web para cargar tres Excel y consultar reportes.
- Reporte HTML con resultados semanales e históricos filtrables.
- Interpretación LLM mediante salida JSON estructurada y revisión humana obligatoria.
- Control de privacidad previo a cualquier cálculo, persistencia o llamada a la API.
- Contexto del LLM limitado a la semana actual más seis anteriores.
- Trece pruebas automatizadas aprobadas el 11/09/2026.

## Documentos de la entrega

- [`prompts/`](prompts/): system prompt real, user prompt y contrato funcional.
- [`corridas/`](corridas/): ocho corridas oficiales y desarrollo histórico preservado.
- [`DECISIONES.md`](DECISIONES.md): iteraciones, fallas, cambios de alcance y cierre.
- [`ANALISIS_ECONOMICO.md`](ANALISIS_ECONOMICO.md): tokens y costos reales, comparación y proyección.
- [`GOBIERNO_Y_RIESGO.md`](GOBIERNO_Y_RIESGO.md): permisos, riesgos, niveles L0–L4 y firma.
- [`MATRIZ_CUMPLIMIENTO.md`](MATRIZ_CUMPLIMIENTO.md): correspondencia con cada requisito.
- [`pruebas/`](pruebas/): evidencia técnica y pruebas de privacidad.
- [`PUBLICACION.md`](PUBLICACION.md): condiciones para una publicación segura.
- [`HERRAMIENTAS_Y_CONECTORES.md`](HERRAMIENTAS_Y_CONECTORES.md): herramientas reales, permisos y trazas operativas.
- [`REPRODUCIBILIDAD.md`](REPRODUCIBILIDAD.md): reconstrucción de versión, configuración, entrada y salida.
- [`ARQUITECTURA_Y_EVOLUCION.md`](ARQUITECTURA_Y_EVOLUCION.md): arquitectura final y evolución de las iteraciones.

## Arquitectura y responsabilidades

```text
Usuario
  │ carga avisos, notificaciones y tareas en sala
  ▼
Control de privacidad y validación de Python
  │ rechazo completo si detecta datos personales
  ▼
Cálculo determinístico + SQLite
  │ métricas semanales e historial
  ▼
LLM con salida estructurada
  │ sólo relaciones y redacción preliminar
  ▼
Reporte HTML
  │
  ▼
Revisión y firma del ingeniero de mantenimiento
```

Python es la única fuente de disponibilidad, horas de parada, cantidad de detenciones y agregaciones. El LLM recibe datos ya calculados, no puede escribir métricas y sus hallazgos se validan contra los avisos conocidos.

## Requisitos

- Python 3.11 o superior.
- Dependencias de `requirements.txt`.
- Una clave de API de OpenAI para completar la interpretación.
- Tres libros Excel válidos por semana: avisos, notificaciones y tareas en sala.

Instalación:

```powershell
cd "ruta\a\Trabajo final"
python -m pip install -r requirements.txt
```

Para reproducir exactamente el entorno evaluado se ofrece además `requirements-lock.txt`, con versiones fijadas.

## Ejecución web local

La clave debe configurarse como variable de entorno y nunca guardarse en el repositorio:

```powershell
$env:OPENAI_API_KEY="tu_clave"
python run_web.py
```

También puede utilizarse `iniciar_web.bat`. Luego abrir `http://127.0.0.1:8000/`.

La página permite ingresar año, semana y período; elegir modelo y nivel; cargar los tres archivos; validar, calcular, guardar, impedir duplicados, reintentar el LLM y abrir los reportes.

Sin `OPENAI_API_KEY`, Python conserva los cálculos pero marca la corrida como incompleta. Después de configurar la clave se debe pulsar **Reintentar LLM**. Un informe sin interpretación no se considera terminado.

## Prueba desde una base vacía

`iniciar_entrega.bat` usa `runtime/entrega_final` como entorno aislado. Si la carpeta no existe, el programa crea una base vacía y la primera semana funciona sin historial previo.

```powershell
$env:OPENAI_API_KEY="tu_clave"
.\iniciar_entrega.bat
```

La combinación año–semana es única. También se pueden incorporar semanas anteriores fuera de orden; el contexto histórico se selecciona cronológicamente y se limita a seis semanas previas.

## Pruebas automatizadas

```powershell
python -m unittest discover -s tests -v
```

La suite cubre base vacía, persistencia estructurada, duplicados, historial, límite de seis semanas, contrato del LLM, tokens y costos, privacidad, autenticación web y procesamiento de cargas.

Reproducción integral con datos sintéticos seguros:

```powershell
python scripts/reproducir_demo.py
```

Esta prueba crea los tres Excel y una SQLite vacía en un directorio temporal, verifica resultados esperados y conserva el manifiesto en `pruebas/evidencia_reproducibilidad/`.

Verificación completa de la entrega en un solo comando:

```powershell
python scripts/verificar_entrega.py
```

## Corridas oficiales

| Semana | Período | Disponibilidad | Parada | Detenciones | Estado LLM |
|---:|---|---:|---:|---:|---|
| 29 | 13/07–19/07 | 98,28 % | 32,23 h | 28 | Completo |
| 30 | 20/07–26/07 | 98,57 % | 26,37 h | 21 | Completo |
| 31 | 27/07–02/08 | 97,89 % | 39,40 h | 39 | Completo |
| 32 | 03/08–09/08 | 97,62 % | 44,19 h | 32 | Completo |
| 33 | 10/08–16/08 | 94,40 % | 106,03 h | 40 | Completo |
| 34 | 17/08–23/08 | 96,69 % | 61,86 h | 33 | Completo |
| 35 | 24/08–30/08 | 97,89 % | 39,35 h | 30 | Completo |
| 36 | 31/08–06/09 | 95,48 % | 83,36 h | 42 | Completo |

Cada carpeta oficial incluye manifiesto de entrada, prompts exactos, validación, resultados, contexto, hallazgos, ejecución del LLM, metadatos y HTML. Los Excel originales no se publican: se identifican mediante nombre y SHA-256 para proteger información operativa y personal.

Las corridas oficiales anteriores a la versión 1.1.0 no capturaron el commit de ejecución; esta limitación está declarada, sin reconstrucción retroactiva. Las nuevas corridas agregan automáticamente versión, hash del código, entorno, ruta de ejecución y hashes de artefactos. La prueba sintética proporciona una ejecución completamente repetible para terceros.

La primera comparación real completó seis llamadas y revisión humana sobre las semanas 29 y 36. Ningún modelo superó todos los umbrales, por lo que se preservó la falla y se mejoró el prompt. La ronda 2 y la selección definitiva permanecen pendientes.

## Reporte e historial

La primera pestaña presenta métricas globales, por serie, sala y puente. La segunda muestra disponibilidad, horas de parada y detenciones por semana, con filtros por semana, puente, sala y serie. También muestra repeticiones en un puente y candidatos de fallas similares entre puentes.

Los puntos de los gráficos llegan calculados desde Python. La interfaz sólo filtra y representa datos; no recalcula indicadores.

## Privacidad y seguridad

Antes de procesar, Python recorre todas las hojas, columnas y valores. Rechaza el lote si detecta posibles nombres, legajos, documentos, correos, teléfonos u otros datos personales. El aviso identifica archivo, hoja y columna sin reproducir el valor detectado.

Los identificadores técnicos reconocidos —equipos, avisos, órdenes, turnos, fechas y horas— no se tratan como documentos personales. El filtro es una barrera preventiva y no reemplaza la revisión humana previa a publicar archivos.

La aplicación local escucha solamente en `127.0.0.1`. Para exponerla en Internet se requieren HTTPS, contraseña y secreto de sesión robustos, almacenamiento persistente y respaldo. Ver `PUBLICACION.md`.

## Gobierno y supervisión

- **L0:** Python valida, calcula y bloquea duplicados.
- **L1:** el LLM propone relaciones preliminares.
- **L2:** el ingeniero revisa cálculos, fuentes, alertas y hallazgos.
- **L3:** el ingeniero firma; el jefe aprueba cambios importantes.
- **L4 no autorizado:** el agente no ordena mantenimiento, no interviene equipos y no modifica SAP ni sistemas de planta.

El reporte no es determinante. Requiere revisión y firma humana antes de tomar decisiones de mantenimiento, seguridad, producción o inversión.

## Datos y respaldos

En ejecución, SQLite guarda información estructurada y la página archiva cada corrida. Para respaldar el historial se debe detener el servidor y copiar `historico.sqlite3`. Los archivos `runtime/`, bases reales, Excel y secretos están excluidos de Git.

## Limitaciones declaradas

- El factor interno de 504 horas por puente requiere validación formal del responsable de mantenimiento.
- La contraseña compartida no ofrece auditoría nominal por empleado.
- El filtro de privacidad puede producir falsos positivos o no detectar casos no contemplados.
- Las relaciones del LLM no demuestran causalidad.
- El código y la evidencia académica están publicados en GitHub; el despliegue público de la aplicación y el dominio todavía están pendientes.
