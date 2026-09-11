# Decisiones del proyecto

## Decisión 021 - Publicación del repositorio académico

**Fecha:** 11 de septiembre de 2026  
**Estado:** implementada

Después de la auditoría se inicializó Git en `Trabajo final`, se integró el commit inicial existente y se publicó la rama `main` en `https://github.com/jonachilano10/Trabajo-final-MBA-Creaci-n-de-agentes`.

El commit publicado excluye los archivos declarados en `.gitignore`. El repositorio contiene código, documentos, pruebas y evidencia reconstruible, pero no contiene la clave de OpenAI, bases SQLite, Excel fuente, ZIP ni `runtime/`. La publicación del repositorio académico no equivale al despliegue productivo de la página web, que continúa sujeto a las condiciones documentadas en `PUBLICACION.md`.

## Decisión 020 - Auditoría previa al repositorio público

**Fecha:** 11 de septiembre de 2026  
**Estado:** implementada

Antes de crear el commit se revisó exactamente la selección preparada por Git. Se comprobaron extensiones, tamaños, reglas de exclusión y patrones de claves API, tokens de GitHub, claves privadas, correos, teléfonos, documentos, legajos y nombres asociados a roles.

No se detectaron secretos ni datos personales en la selección publicable. `runtime/`, SQLite, Excel, ZIP, `.env` real y cachés quedaron fuera. Los avisos, órdenes, códigos de equipo y textos técnicos permanecen porque constituyen la evidencia real del caso y están permitidos por el contrato. Se declaró como riesgo residual que esos datos son operativos y que una versión productiva debe mantenerlos detrás de autenticación.

El resultado detallado quedó en `pruebas/AUDITORIA_PRE_PUBLICACION.md`. Esta auditoría debe repetirse si se agregan archivos después del cierre.

## Decisión 019 - Cierre documental y evidencia publicable

**Fecha:** 11 de septiembre de 2026  
**Estado:** implementada; carpeta preparada para auditoría de privacidad y publicación

Las ocho corridas oficiales se copiaron desde el entorno aislado `runtime/entrega_final/corridas` hacia `corridas/`, que es la ubicación exigida por la consigna y no está excluida de Git. Cada carpeta conserva manifiesto de entrada con SHA-256, prompts exactos, validación, JSON estructurados, uso del LLM, metadatos y reporte HTML.

Los Excel originales no se copiaron a la evidencia publicable. Esta decisión protege información personal y operativa, y es coherente con el gobierno del sistema. La entrada se identifica mediante nombre y huella; los datos derivados efectivamente utilizados permanecen en `resultados.json` y `contexto_llm.json`.

Las siete corridas anteriores se movieron, sin borrarlas ni reescribirlas, a `corridas/desarrollo_historico/`. De este modo el evaluador encuentra primero la secuencia oficial, mientras que los errores e iteraciones continúan disponibles como evidencia honesta del proceso.

Se actualizaron `README.md`, `MATRIZ_CUMPLIMIENTO.md`, `ANALISIS_ECONOMICO.md` y este documento. La publicación en GitHub y el despliegue externo permanecen pendientes y no se presentan como completados.

## Decisión 018 - Secuencia oficial de semanas 29 a 36

**Fecha de ejecución:** 9 y 11 de septiembre de 2026  
**Estado:** completada

Se ejecutó el agente desde una base SQLite vacía y se incorporaron manualmente ocho semanas consecutivas. Todas superaron validación, quedaron almacenadas sin duplicados y completaron la interpretación con `gpt-5.4-mini` y razonamiento `medium`.

| Semana | Disponibilidad | Parada | Detenciones | LLM |
|---:|---:|---:|---:|---|
| 29 | 98,28 % | 32,23 h | 28 | Completado |
| 30 | 98,57 % | 26,37 h | 21 | Completado |
| 31 | 97,89 % | 39,40 h | 39 | Completado |
| 32 | 97,62 % | 44,19 h | 32 | Completado |
| 33 | 94,40 % | 106,03 h | 40 | Completado |
| 34 | 96,69 % | 61,86 h | 33 | Completado |
| 35 | 97,89 % | 39,35 h | 30 | Completado |
| 36 | 95,48 % | 83,36 h | 42 | Completado |

Las semanas 31 y 36 se cargaron únicamente después de retirar las columnas personales que habían provocado el rechazo deliberado documentado en la Decisión 014. Los archivos confidenciales originales no se incorporaron a la base ni a las corridas oficiales.

El consumo acumulado informado por la API fue de 171.827 tokens y US$ 0,297467. El promedio observado fue US$ 0,037183 por corrida. La semana 36 ejercitó el límite de contexto: recibió como máximo las seis semanas anteriores y aprovechó caché de entrada. Estos valores reemplazan las estimaciones como evidencia económica principal, sin borrar los escenarios comparativos.

La secuencia demuestra los casos de base vacía, crecimiento histórico, filtros por semana/equipo/sala/serie, recurrencias, control de duplicados, límite de contexto y trazabilidad automática. Los hallazgos LLM siguen siendo preliminares y deben ser revisados y firmados por el ingeniero.

## Decisión 017 - Un único system prompt real para el LLM

**Fecha:** 9 de septiembre de 2026  
**Estado:** implementada; reemplaza la separación de prompts definida en la Decisión 015

Se corrigió la diferencia entre el archivo denominado system prompt y la instrucción utilizada por la API. `prompts/system_prompt.md` contiene ahora el prompt exacto enviado al LLM mediante `instructions`, con las seis piezas de la consigna: rol, contexto, tarea, fuentes y restricciones, formato de salida y ejemplos.

La especificación extensa anterior se preservó como `prompts/contrato_funcional_agente.md`. Ese documento describe el sistema completo y las reglas determinísticas que ejecuta Python, pero no se presenta como texto enviado al modelo. Se eliminó `llm_instructions.md` para evitar dos fuentes de verdad.

El programa carga directamente `prompts/system_prompt.md`, las pruebas verifican igualdad exacta y las nuevas corridas archivan ese archivo como `SYSTEM_PROMPT.txt`. También guardan el contrato funcional para explicar cómo se implementan privacidad, cálculos, historial y reportes fuera del LLM. La estimación económica incluye ahora el system prompt, el JSON histórico y el esquema de salida estructurada.

Las corridas históricas no se reescriben: conservan los prompts disponibles en la fecha en que fueron realizadas.

## Decisión 016 - Entorno separado para las corridas finales

**Fecha:** 9 de septiembre de 2026  
**Estado:** implementada

Se creó `runtime/entrega_final` como almacenamiento aislado para ejecutar la secuencia final desde una base SQLite vacía. La selección se realiza mediante `AGENT_DATA_DIR` y no modifica `data/historico.sqlite3`, `salidas/` ni las corridas históricas existentes. El iniciador `iniciar_entrega.bat` conserva el entorno entre ejecuciones para permitir que el historial crezca semana a semana; no elimina datos automáticamente.

La inicialización y el conteo de cero semanas se documentan en `pruebas/VALIDACION_BASE_VACIA.md`. Las semanas 31 y 36 no podrán incorporarse desde los archivos confidenciales de prueba: se necesitarán copias depuradas, manteniendo los originales como evidencia negativa.

## Decisión 015 - Prompt operativo reducido y trazabilidad automática

**Fecha:** 9 de septiembre de 2026  
**Estado:** reemplazada por la Decisión 017; se conserva como historial de diseño

En esta iteración se había separado el system prompt funcional completo de una instrucción reducida conservada en `prompts/llm_instructions.md`. La revisión posterior determinó que esa nomenclatura podía impedir demostrar cuál era el system prompt efectivamente utilizado. La Decisión 017 reemplazó este diseño por un único `prompts/system_prompt.md` real y movió la especificación extensa a un contrato funcional claramente identificado.

Cada nueva corrida web archiva el system prompt, el user prompt completado, su plantilla, la instrucción exacta del LLM, huellas de las fuentes, contexto, hallazgos, ejecuciones con tokens y costos, validación, HTML y `METADATA.json`. Si la API falla, el estado queda como pendiente; un reintento actualiza la evidencia LLM y el reporte sin modificar los cálculos de Python.

Las corridas históricas se mantienen tal como fueron producidas y sus faltantes se declaran en `corridas/README.md`. No se agregan retroactivamente prompts, tokens ni costos que no fueron registrados en su ejecución original.

## Decisión 014 - Archivos confidenciales conservados como prueba negativa

**Fecha:** 9 de septiembre de 2026  
**Estado:** prueba ejecutada correctamente

El lote comprimido de las semanas 29, 30, 31, 32 y 36 incluyó deliberadamente archivos con columnas personales para demostrar el control de privacidad. El agente rechazó la semana 31 por las columnas `Nombre del empleado` y `Número de personal` de Notificaciones. También rechazó la semana 36 por esas columnas de Notificaciones y por la columna `Nombre y Apellido` de Avisos.

El rechazo ocurrió antes de calcular, escribir en SQLite o invocar al LLM. No se mostraron ni guardaron los valores detectados y no se modificaron los archivos originales. Las semanas 29, 30 y 32 superaron el control de privacidad y la validación estructural preliminar, pero no se guardaron durante esta prueba.

Los archivos rechazados se conservarán fuera del repositorio público como evidencia negativa identificada mediante SHA-256. Para las corridas históricas de las semanas 31 y 36 deberán utilizarse copias depuradas con nombres diferentes. El detalle reproducible de la prueba se encuentra en `pruebas/PRUEBA_PRIVACIDAD_SEMANAS_31_Y_36.md`.

## Decisión 013 - Gobierno actualizado y rechazo de información confidencial

**Fecha:** 8 de septiembre de 2026  
**Estado:** implementada

Se incorporó al repositorio el cuestionario respondido `PREGUNTAS_GOBIERNO_Y_RIESGO_TEMPLATE.md` y se reconstruyó `GOBIERNO_Y_RIESGO.md` con las decisiones operativas: acceso para ingeniería y jefatura de mantenimiento, web pública con contraseña, revisión y firma en papel por el ingeniero, hallazgos LLM no determinantes, SAP futuro sólo lectura con autorización de IT, Power BI permitido y notificaciones por correo prohibidas. También se documentaron limitaciones actuales, respaldo pendiente y falta de auditoría nominal por utilizar una contraseña compartida.

La página web pública preparada en la Decisión 012 mantiene protegidas la carga, los reportes y las ejecuciones. Antes de cualquier análisis, un nuevo control de Python abre los tres Excel en modo lectura y recorre todas sus hojas, columnas y valores. Busca columnas personales, nombres completos, nombres asociados a operarios o supervisores, legajos de cinco dígitos, posibles documentos de siete a nueve dígitos, correos y teléfonos.

Si encuentra un patrón confidencial, rechaza el lote completo antes de calcular, guardar en SQLite o invocar al LLM. El mensaje indica archivo, hoja y columna para depuración, pero no reproduce ni almacena el valor detectado. Los códigos P-MG, turnos, fechas, horas y números ubicados en columnas técnicas de aviso, orden o notificación se aceptan para evitar falsos positivos con los identificadores operativos reales.

La misma regla se agregó al system prompt final para que el contrato y el comportamiento determinístico sean coherentes. Python es el control efectivo; el prompt por sí solo no se considera una barrera de privacidad. Se añadieron pruebas de rechazo y aceptación de patrones y se verificó que los tres archivos reales de la semana 35 superen el filtro sin observaciones.

## Decisión 012 - Página pública protegida por contraseña

**Fecha:** 8 de septiembre de 2026  
**Estado:** implementada para despliegue; publicación externa pendiente de proveedor y dominio

Se reutilizó la página web del agente para permitir el acceso remoto de empleados mediante una contraseña compartida. Se agregaron sesiones firmadas de ocho horas, cookies protegidas, control de formularios, límite de intentos de ingreso, cabeceras de seguridad y protección de reportes y ejecuciones. La contraseña, el secreto de sesión y la clave de OpenAI se configuran como secretos y no se escriben en el código.

La aplicación se niega a iniciar en una interfaz pública cuando la contraseña tiene menos de 12 caracteres o el secreto de sesión menos de 32. Se agregó un `Dockerfile` y soporte para almacenamiento persistente, manteniendo SQLite, reportes y corridas fuera de la imagen descartable.

**Límite aceptado:** una contraseña compartida controla el acceso, pero no identifica individualmente a cada empleado. Para auditoría nominal deberá incorporarse autenticación por usuario o inicio de sesión corporativo. La publicación efectiva requiere elegir un proveedor, configurar HTTPS, secretos, dominio y respaldo; no se inventó una URL pública ni se expusieron datos desde el equipo local.

## Decisión 010 - Evidencia económica y pruebas reproducibles

**Fecha:** 8 de septiembre de 2026  
**Estado:** implementada

Se incorporó una comparación económica para GPT-5.4, GPT-5.4 Mini y GPT-5.4 Nano, con niveles `none`, `low`, `medium`, `high` y `xhigh`. Las simulaciones usan el mismo volumen de tokens para no atribuir consumos inventados a cada nivel.

La aplicación guarda en SQLite el uso real devuelto por la API: entrada, entrada cacheada, salida, razonamiento, total y costo. Las corridas previas no tienen medición retroactiva. Se agregó `pruebas/` con la suite, la matriz económica y el protocolo para elegir el modelo más chico que haga bien la tarea.

## Decisión 011 - Ventana histórica máxima de seis semanas

**Fecha:** 8 de septiembre de 2026  
**Estado:** implementada

La base SQLite continúa conservando todas las semanas cargadas, pero el contexto enviado al LLM incluye únicamente la semana actual y, como máximo, las seis semanas almacenadas inmediatamente anteriores. La selección se realiza por año y número de semana, por lo que también funciona cuando las semanas históricas se incorporan fuera de orden.

**Motivo:** sin un límite, el contexto y el consumo de tokens crecerían de manera indefinida a medida que se acumulara información. La ventana móvil establece un máximo operativo previsible, reduce costo y latencia y mantiene comparaciones recientes. El tamaño real todavía puede variar según la cantidad y extensión de fallas dentro de esas siete semanas.

El límite se aplica mediante Python y fue incorporado también al system prompt para que el contrato describa el comportamiento real. Una prueba automatizada carga ocho semanas y confirma que la más antigua queda fuera del contexto del LLM. Los gráficos históricos y cálculos de Python siguen consultando el historial completo.

## Propósito

Este documento registra la evolución real del agente de análisis semanal de mantenimiento. Su objetivo es permitir que un tercero entienda qué se intentó, qué falló, qué se modificó y qué falta validar.

## Estado al 5 de septiembre de 2026

El proyecto se encuentra en una etapa de prototipo funcional basado en prompts. Ya se realizaron pruebas con archivos Excel reales y se generaron libros de análisis e informes HTML. Todavía no existe una aplicación ejecutable autónoma, un esquema JSON validado, tests automatizados ni los documentos de economía y gobierno requeridos para la entrega final.

Los artefactos históricos se organizaron en `corridas/`. Las primeras tres carpetas representan iteraciones sobre la semana 33 y no deben presentarse engañosamente como tres períodos independientes. También se localizó un informe de la semana 34, que queda registrado como corrida adicional provisional.

## Alcance elegido

El sistema recibe tres archivos semanales:

1. tareas programadas en sala;
2. avisos de emergencia;
3. notificaciones de mantenimiento.

Debe validar los datos, calcular disponibilidad para 12 puentes grúa, relacionar avisos con notificaciones mediante la orden de trabajo, analizar fallas y producir una salida comparable. No modifica los archivos fuente ni ejecuta acciones en SAP.

## Decisión 001 - Caso de uso acotado

**Fecha aproximada:** agosto de 2026  
**Estado:** vigente

Se eligió automatizar el informe semanal de disponibilidad y fallas de 12 puentes grúa. Se descartó por el momento ampliar el alcance a SAP, mantenimiento predictivo, Power BI, envío automático de correos y diagnóstico autónomo de causa raíz.

**Motivo:** el trabajo final exige un sistema real, demostrable y reproducible. Un alcance más amplio aumentaría el riesgo de entregar componentes incompletos.

## Decisión 002 - Vinculación por orden y control por equipo

**Fecha aproximada:** agosto de 2026  
**Estado:** vigente, pendiente de automatización

Los avisos y las notificaciones se vinculan por número de orden de trabajo. El TAG del equipo se utiliza como control secundario para evitar relacionar registros pertenecientes a equipos diferentes.

**Restricción:** si la orden coincide pero el equipo no coincide, la vinculación debe marcarse para revisión y no aceptarse silenciosamente.

## Iteración 1 - Primera corrida de la semana 33

**Fecha de los artefactos:** 25 de agosto de 2026  
**Objetivo:** calcular la disponibilidad de la semana 33, del 10/08/2026 al 16/08/2026.

### Resultado

El agente generó un libro Excel con disponibilidad total de 94,41 %. Utilizó 168 horas calendario por equipo.

### Falla observada

El resultado no respetó la definición operativa indicada por el usuario, que requería utilizar una base de 504 horas por equipo debido a la condición de respaldo entre puentes.

### Cambio decidido

Se agregó una instrucción explícita: utilizar 504 horas por equipo y no sustituir esa base por las 168 horas calendario de una semana.

### Aprendizaje

Cuando una regla interna difiere de una convención habitual, debe quedar expresada como restricción inequívoca, justificada y acompañada por un ejemplo de control.

## Decisión 003 - Base de 504 horas

**Fecha:** 25 de agosto de 2026  
**Estado:** provisional; requiere validación formal del responsable

Se adoptó la siguiente fórmula:

```text
Tiempo disponible = 504 h - horas de mantenimiento solicitado
Disponibilidad = (tiempo disponible - horas de parada) / tiempo disponible
```

La justificación registrada es que los puentes funcionan como respaldo entre sí y la medición interna multiplica la base semanal por tres.

**Pendiente crítico:** documentar qué representa exactamente el factor 3, quién aprueba la definición y si el indicador debe denominarse disponibilidad operativa interna para distinguirlo de la disponibilidad calendario tradicional.

## Iteración 2 - Corrección de la base de cálculo

**Fecha de los artefactos:** 25 de agosto de 2026  
**Objetivo:** recalcular la semana 33 con 504 horas.

### Resultado

El agente informó una disponibilidad total de 98,21 % y actualizó el libro Excel.

### Falla observada

La salida seguía sin ser suficientemente comparable entre períodos y no se generaba como HTML. Además, una revisión posterior mostró una inconsistencia en las horas de parada: el archivo fuente suma 106,03 h para 40 avisos con parada, mientras que los libros de las iteraciones 1 y 2 conservan 99,01 h.

### Cambio decidido

Se definió una estructura fija de informe HTML con:

- período y número de semana;
- disponibilidad global, por serie, sala y equipo;
- avisos y horas de detención;
- análisis de fallas e intervenciones;
- observaciones y acciones sugeridas;
- diseño y orden de campos estables.

## Decisión 004 - Separar cálculo y redacción

**Fecha de registro:** 5 de septiembre de 2026  
**Estado:** aprobada para la siguiente etapa

Los cálculos, filtros, vinculaciones y controles se implementarán mediante código determinístico. El modelo de lenguaje se reservará para clasificación semántica, síntesis y redacción.

**Motivo:** los valores numéricos deben poder repetirse, probarse y auditarse sin depender del comportamiento variable de un modelo.

## Iteración 3 - Informe HTML de la semana 33

**Fecha de los artefactos:** 25 de agosto de 2026  
**Objetivo:** producir una salida visual comparable y corregir el total de horas de parada.

### Resultado

Se generaron:

- un informe HTML de la semana 33;
- un libro Excel actualizado;
- disponibilidad global de 98,21 %;
- 40 avisos con detención;
- 106,03 h de detención.

### Mejora pendiente

Faltó implementar un checklist de calidad. El prompt también indicaba que un dato no calculable debía omitirse; esta regla se considera riesgosa y será reemplazada por errores o advertencias explícitas.

## Corrida adicional localizada - Semana 34

**Fecha del artefacto:** 25 de agosto de 2026  
**Estado:** provisional; falta metadata completa

Se encontró un HTML correspondiente al período 17/08/2026 al 23/08/2026. Informa:

- disponibilidad global: 98,96 %;
- avisos con detención: 33;
- horas de detención: 61,86 h;
- equipos analizados: 12.

Esta corrida utiliza datos reales, pero no conserva todavía en una misma carpeta el prompt exacto, la respuesta conversacional, el modelo, los tokens ni un log de validación.

## Decisión 005

-Se justifica en system_prompt el factor de multiplicar por tres.
-Se aclara con palabras en el contrato el cálculo de la disponibilidad por puente,por sala, por serie y global. Identificando lo que es disponibilidad por puente y disponibilidad agregada por compartir funcionalidades entre puentes de misma sala. Se restringe el cálculo por promedios simples.
-Se añade en salida que los valores repetidos deben señarlarse o marcarse.
-Se añade que cuando haya superposición entre parada de equipo e intervención de mantenimiento se haga notar para que el humano elija.
-Se restringe que sólo se deben tener en consideración los datos de los 12 puentes. El resto de los equipos se deben ignorar.

Al correr nuevamente los archivos de la semana 33 (ejecución realizada 5/9/2026) y al comparar con la ejecutada (21/08/2026) se obtienen valores distintos. Esto se debe a que la primera corrida fue ejecutada con otras bases de valores para el tiempo calendario y tiempo disponible de equipos.

## Decisión 006
-Se agrega análisis histórico de fallas al system_prompt.
-Se solicita que realice una segunda pestaña en el HTML con gráficos de disponibilidad, horas de parada y cantidad de detenciones. 
-Se ejecuta una corrida nuevamente con la semana 33 y se documenta en el repositorio.
-Los valores de disponibilidad coinciden con la corrida 2.
-La ejecución tuvo errores: no mostró la cantidad de avisos con detenciones, ni las horas de detención y los gráficos no fueron los esperados. Se gráfico en el eje Y el valor de disponibilidad y en el eje X el puente. Se pretendía que el eje X sea el npumero de semana y que se pueda filtrar por disponibilidad, cantidad de paradas y horas de detención. Se modificará en el system_prompt.

##Decisión 007
-Se ejecuta corrida en nuevo chat de work de GPT, se obtiene el resultado esperado tanto en gráficos como en valores. Sólo faltó mostrar en la pestaña 1 el valor de disponibilidad de sala 1 y serie A.
-En la decisión 6 y corrida anterior, el archivo de salida HTML se generó a partir de la información almacenada. Esto cambió al abrir un nuevo chat y cargar los archivos nuevamente.

## Decisión 008 - Interpretación LLM obligatoria y no determinante

**Fecha:** 7 de septiembre de 2026  
**Estado:** implementada

Cada corrida terminada debe incluir interpretación del LLM sobre las fallas y relaciones históricas. Esa interpretación se presenta siempre como preliminar, no determinante y sujeta a revisión humana obligatoria. No reemplaza el diagnóstico técnico ni puede modificar valores calculados por Python.

Cuando la etapa LLM aún no fue completada, el HTML identifica la corrida como incompleta y no debe considerarse un informe final.

## Decisión 009 - Página web local para cargar las semanas

**Fecha:** 7 de septiembre de 2026  
**Estado:** implementada

El agente incorpora una página web local para ingresar período y cargar los tres Excel. La interfaz reutiliza el cálculo determinístico, SQLite, el control de duplicados y el generador HTML existentes. Los archivos cargados se procesan en un directorio temporal, se cierran y se eliminan sin modificar los originales.

La interpretación preliminar se integra mediante la Responses API con salida JSON estructurada. La clave se lee desde `OPENAI_API_KEY` y no se guarda en el proyecto. Si la API no está configurada o falla, los cálculos permanecen guardados pero la corrida se identifica como incompleta y puede reintentarse.
