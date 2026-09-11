# Gobierno, riesgo y supervisión

Documento operativo y técnico elaborado a partir de las respuestas conservadas en [`PREGUNTAS_GOBIERNO_Y_RIESGO_TEMPLATE.md`](PREGUNTAS_GOBIERNO_Y_RIESGO_TEMPLATE.md).

## Alcance y responsables

El agente se utiliza en una planta de manufactura de Puerto Madryn con 12 puentes grúa. Cada lunes se analiza la semana anterior. Pueden acceder ingenieros de mantenimiento y el jefe del sector; la información no se distribuye automáticamente a gerencia.

El ingeniero de mantenimiento ejecuta, revisa y aprueba el reporte. Los cambios importantes son supervisados por el jefe de mantenimiento. El informe se imprime y firma en papel. Ante una disponibilidad anormal, el ingeniero investiga y documenta la decisión utilizando la información del agente.

## Sistemas, datos y permisos

El agente:

- lee los tres Excel seleccionados por el usuario;
- escribe resultados dentro del almacenamiento de `Trabajo final`;
- consulta SQLite;
- envía al LLM únicamente el contexto textual estructurado preparado por Python;
- no modifica los Excel originales;
- no escribe en SAP, no envía correos y no actúa sobre equipos.

Una futura integración con SAP requiere autorización de IT y debe ser de solo lectura con aprobación. Puede evaluarse una salida hacia Power BI. La notificación automática por correo está prohibida.

La clave API, contraseña y secreto de sesión se proporcionan mediante variables de entorno y no se guardan en el repositorio.

## Autonomía L0-L4

- **L0:** Python valida archivos, calcula métricas y bloquea duplicados mediante reglas reproducibles.
- **L1:** el LLM propone relaciones y explicaciones preliminares entre fallas.
- **L2:** el ingeniero revisa cada hallazgo, los cálculos y las advertencias.
- **L3:** el ingeniero firma el informe; el jefe aprueba cambios importantes.
- **L4 no autorizado:** el agente no ordena ni ejecuta mantenimiento, no interviene equipos y no modifica sistemas de planta.

Los hallazgos del LLM son sugerencias. Si el usuario detecta una alucinación, debe marcar el hallazgo y puede repetir la comparación con un modelo de mayor capacidad. Nunca se debe ordenar mantenimiento basándose exclusivamente en el LLM.

## Riesgos y respuesta

| Riesgo | Prevención/detección | Respuesta |
|---|---|---|
| Excel corrupto o con estructura incorrecta | Validación automática | Rechazar la carga |
| Semana equivocada | Validar período y contenido | Mostrar error y explicación |
| Información personal o confidencial | Control previo implementado y probado con casos unitarios y archivos deliberadamente preparados | Rechazar todo el lote y avisar qué archivo requiere depuración, sin reproducir el dato sensible |
| Semana duplicada | Restricción única año-semana | Avisar y no insertar |
| Corte durante una corrida | Archivos temporales y transacción SQLite | Descartar la ejecución incompleta y reintentar |
| API no disponible | Manejo explícito del error | Conservar cálculo y marcar corrida incompleta |
| Alucinación del LLM | Lectura humana obligatoria | Marcar hallazgo; no actuar; contrastar si corresponde |
| Corrupción de SQLite | Respaldo requerido | Restaurar última copia verificada |
| Contraseña filtrada | Secreto externo y límite de intentos | Rotar contraseña y secreto de sesión |
| Acceso sin cifrado | HTTPS en el proveedor | No exponer directamente el puerto local |

El riesgo considerado más peligroso es que una alucinación derive en mantenimiento innecesario. Debe detectarlo el ingeniero antes de aprobar y firmar.

## Trazabilidad y discrepancias

SQLite conserva semana, fecha, huellas de los Excel, cálculos, avisos y resultados. No se registra qué empleado realizó la carga porque se utiliza una contraseña compartida. Por lo tanto existe trazabilidad de datos, pero no auditoría nominal.

Cuando el jefe discrepe de un indicador, prevalece su decisión operativa, pero el agente debe mostrar el detalle de los cálculos para permitir la auditoría. Una corrección de una semana debe conservar la corrida anterior y crear una corrida paralela; esta función todavía no está disponible desde la web porque el control de duplicados protege la semana almacenada.

Sólo el ingeniero de mantenimiento y el jefe están autorizados a solicitar que se deshaga una corrida. La interfaz actual no permite borrar datos.

## Controles pendientes

- Configurar respaldo automático de SQLite y realizar una prueba de restauración.
- Preparar un instructivo operativo y una demostración de cinco minutos.
- Definir cómo versionar una semana corregida sin eliminar la evidencia anterior.
- Si se necesita saber quién realizó cada carga, sustituir la contraseña compartida por usuarios individuales.

## Firma y revisión

El agente produce un informe técnico preliminar. El ingeniero de mantenimiento debe revisar los archivos, cálculos y hallazgos y firmar en papel antes de cualquier decisión de mantenimiento, seguridad, producción o inversión. Se prevé una auditoría semestral del proceso.
