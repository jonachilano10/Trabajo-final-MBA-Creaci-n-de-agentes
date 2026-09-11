# CUESTIONARIO GOBIERNO Y RIESGO - RESPUESTAS RÁPIDAS

**Instrucciones:** Responde brevemente cada pregunta (1-3 líneas). Si no aplica, pone "N/A".

\---

## BLOQUE 1: QUIÉN USA EL AGENTE

**1.1** - ¿Quién tiene acceso a la web pública?

```
Respuesta: Ingenieros de mantenimiento hasta jefe del sector. No llega a gerencia.
```

**1.2** - ¿Quién APRUEBA usar los reportes?

```
Respuesta: El ingeniero de mantenimiento
```

**1.3** - ¿Es web pública con contraseña, solo VPN, o totalmente abierta?

```
Respuesta: Web pública con contraseña
```

\---

## BLOQUE 2: DATOS Y BASE DE DATOS

**2.1** - Si alguien carga un Excel corrupto, ¿debería rechazarse automático o avisar?

```
Respuesta: Deberia rechazarse en automático.
```

**2.2** - ¿Debería haber un "audit log" de quién insertó qué semana en SQLite?

```
Respuesta: No
```

**2.3** - Si se corta la luz durante una corrida, ¿qué pasa? (¿queda incompleta, se reintenta, se borra?)

```
Respuesta: Se borra
```

\---

## BLOQUE 3: ALUCINACIONES DEL LLM

**3.1** - Los hallazgos del LLM, ¿son DETERMINANTES para actuar o SUGERENCIAS para revisar?

```
Respuesta: sugerencias para revisar
```

**3.2** - Si el LLM alucina un hallazgo falso, ¿quién lo detecta? (¿usuario leyendo o validación automática?)

```
Respuesta: El usuario leyendo 
```

**3.3** - Si se detecta alucinación, ¿descartar TODO, marcar solo ese hallazgo, o cambiar a modelo más caro?

```
Respuesta: Marcar el hallazgo y recomendar cambiar a modelo más caro para ver si pasa lo mismo 
```

\---

## BLOQUE 4: NIVELES DE AUTONOMÍA (L0-L4)

**4.1** - ¿El jefe corre el agente y confía ciegamente, o revisa y firma antes de usar?

```
Respuesta: Revisa y firma antes de usar
```

**4.2** - ¿Existe un proceso formal para auditar decisiones pasadas o cambiar decisiones de mtto?

```
Respuesta: No 
```

**4.3** - Si agente dice "78%" pero jefe cree "85%", ¿quién tiene razón? ¿Hay proceso para auditar?

```
Respuesta: El jefe tiene razón, pero el agente debe mostrar los cálculos realizados cuando exista discrepancia.
```

\---

## BLOQUE 5: FALLOS Y RECUPERACIÓN

**5.1** - De estos, ¿cuál es el fallo MÁS PELIGROSO? (marca con X)

```
☐ A) Excel corrupto
☐ B) API OpenAI cae
☐ C) SQLite se corrompe (pérdida de histórico)
☐ D) Usuario carga datos de semana equivocada
x E) LLM alucina → se ordena mtto innecesario
☐ F) Otro: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
```

**5.2** - Si pasa el fallo más peligroso, ¿cuánto tiempo para detectarlo y quién lo detecta?

```
Respuesta: Lo detecta el ingeniero de mantenimiento previo a aprobar.
```

**5.3** - ¿Existe backup automático de SQLite? (¿Dónde? ¿Con qué frecuencia? ¿Probaron recuperar?)

```
Respuesta: No por el momento no existe.
```

\---

## BLOQUE 6: AUDITORÍA Y COMPLIANCE

**6.1** - ¿Hay regulación o auditoría sobre decisiones de mtto/disponibilidad en tu empresa?

```
Respuesta: No
```

**6.2** - Si auditor pregunta "¿Por qué bajó disponibilidad a 75%?", ¿tienes pista de auditoría? (quién, cuándo, qué Excel, quién aprobó)

```
Respuesta: Si
```

**6.3** - ¿GOBIERNO\_Y\_RIESGO.md debe estar en repo técnico (devs), manual de procedimientos (operadores), o ambos?

```
Respuesta: ambos
```

\---

## BLOQUE 7: INTEGRACIÓN CON SISTEMAS

**7.1** - En futuro, ¿el agente PODRÍA leer SAP, enviar a Power BI, notificar email? ¿Cuál ESTÁ PROHIBIDA?

```
Respuesta: Podría leer SAP, enviar a Power Bi y no notificar email.
```

**7.2** - Si se integra con SAP, ¿quién AUTORIZA? (TI, mtto, ambos, votación)

```
Respuesta: IT
```

**7.3** - Si se integra con SAP, ¿solo lectura, o escritura? ¿Automática o con aprobación?

```
Respuesta: Lectura con aprobación
```

\---

## BLOQUE 8: COMUNICACIÓN DE RESULTADOS

**8.1** - Cuando se genera reporte HTML, ¿qué pasa después? (email, intranet, imprime+firma, archiva)

```
Respuesta: imprime+firma
```

**8.2** - Si disponibilidad baja a 60%, ¿quién es responsable de investigar y documentar decisión?

```
Respuesta: El ingeniero de mantenimiento usando la información del agente.
```

**8.3** - Hallazgos LLM, ¿QUIÉN FIRMA que está de acuerdo? (digital/papel) ¿DÓNDE se guarda?

```
Respuesta: Firma el ingeniero de mantenimiento en papel
```

\---

## BLOQUE 9: CAMBIOS Y ROLLBACK

**9.1** - Si se descubre que datos de semana 35 eran malos y quieren procesar de nuevo, ¿qué pasa?

```
☐ Se borra histórico anterior
☐ Se guarda versión anterior para auditoría
X Se crea nueva corrida paralela
☐ Otro: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
```

**9.2** - ¿Quién tiene permiso para deshacer/borrar una corrida? (jefe mtto solo, jefe+industrial, nunca)

```
Respuesta: ingeniero de mantenimiento y jefe
```

**9.3** - Si se deshace una corrida, ¿se notifica a quién? ¿Se registra en log? ¿Se mantiene versión anterior?

```
Respuesta: No se notifica
```

\---

## BLOQUE 10: EDUCACIÓN Y ERRORES

**10.1** - Si usuario carga Excel viejo (semana 30 en lugar de 35), ¿qué debería pasar?

```
X Mensaje de error claro
X Explicación de por qué
☐ Opción para ver histórico
☐ Todas
☐ Otro: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
```

**10.2** - ¿Existe "runbook" (manual) que documenta cómo usar, qué hacer si falla, a quién contactar?

```
Respuesta: No
```

**10.3** - ¿Necesita capacitación? (5 min demo, 1h training, autodidacta, otro)

```
Respuesta: 5 min demo
```

\---

## CONTEXTO GENERAL (optativo pero útil)

**CONTEXTO-1** - Describe en 2-3 líneas tu operación real:

```
Respuesta: Somos planta de manufactura en Puerto Madryn con 12 puentes grúa. 
Ingeniero de mantenimiento ejecuta y Jefe de mtto supervisa aprueba cambios importantes. 
Cada lunes se ejecuta análisis de semana anterior. Auditoría cada 6 meses.
```

**CONTEXTO-2** - ¿Cuál es la PEOR cosa que podría pasar si el agente falla?

```
Respuesta: Pérdida de tiempo por analizar cosas que no son reales
```

**CONTEXTO-3** - ¿Cuál es el MEJOR resultado que esperas del documento GOBIERNO\_Y\_RIESGO.md?

```
Respuesta: Que cualquier operario nuevo entienda exactamente qué confiar del agente y qué revisar.
```

\---

## ✅ CHECKLIST - Antes de enviar

* \[x ] Respondí todas las preguntas que aplican a mi caso
* \[ x] Marqué con X donde había opciones
* \[ si] Fui honesto (si no sé, puse "No sé" o "N/A")
* \[ si] Incluí contexto general si es relevante

\---

## 📤 INSTRUCCIONES DE ENTREGA

Copia todo este archivo, reemplaza `Respuesta:` con TUS respuestas, y envíame.

Ejemplo de cómo debería verse:

```markdown
\*\*1.1\*\* - ¿Quién tiene acceso a la web pública?
Respuesta: Jefe de mantenimiento, 2 supervisores, y consultores externos (con VPN)

\*\*1.2\*\* - ¿Quién APRUEBA usar los reportes?
Respuesta: Jefe de mantenimiento firma, luego jefe industrial da el OK para acciones correctivas
```

\---

¡Listo! Podés responder y enviar cuando esté.


