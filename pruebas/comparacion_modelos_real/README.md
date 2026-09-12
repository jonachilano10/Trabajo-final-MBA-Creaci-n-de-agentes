# Comparación real de modelos

Esta carpeta recibirá la prueba paga necesaria para cerrar **AE-03**. No contiene resultados simulados presentados como reales.

## Estado de la primera ejecución real

La prueba finalizó el 11/09/2026 con seis llamadas y un costo total de **US$ 0,30482527**. Todos los avisos citados existen. El análisis objetivo posterior encontró dos errores de alcance:

- GPT-5.4 Nano: 1 de 19 hallazgos `same_bridge` mezcló P-MG11 y P-MG21.
- GPT-5.4 Mini: 1 de 17 hallazgos `same_bridge` mezcló P-MG21 y P-MG22.
- GPT-5.4: 0 errores de alcance en 21 hallazgos.

Por el umbral previo, sólo GPT-5.4 avanza a revisión humana. Esta falla produjo la versión 1.2.0 del agente, que agrega el control faltante al prompt y a Python. Los resultados no se corrigieron ni ocultaron.

## Diseño previo a la ejecución

- Casos: semanas 29 y 36, para cubrir una semana inicial y otra con la ventana histórica completa.
- Configuraciones: GPT-5.4 Nano, GPT-5.4 Mini y GPT-5.4, todas con razonamiento `medium`.
- Mismo contexto, prompt, esquema y regla de validación.
- La base oficial se copia a un directorio temporal; no se modifican sus hallazgos.

## Umbral de suficiencia

Una configuración es técnicamente suficiente cuando, considerando ambos casos:

1. completa todas las llamadas con JSON válido;
2. no inventa avisos, métricas ni causas;
3. no presenta ninguna afirmación causal no respaldada;
4. obtiene al menos 80 % en corrección de relaciones revisadas;
5. obtiene un promedio mínimo de 1,5/2 en utilidad para revisión humana.

Se elegirá la configuración de menor costo real que supere todos los umbrales. Los criterios se fijaron antes de ejecutar para evitar seleccionar el resultado por conveniencia.

## Ejecución

```powershell
$env:OPENAI_API_KEY="tu_clave"
python scripts/comparar_modelos.py `
  --db "runtime\entrega_final\data\historico.sqlite3" `
  --semanas 29 36 `
  --confirmar-pruebas-pagas
```

El programa generó `resultados_api.json`, `MANIFIESTO.json` y `evaluacion_humana.csv`. `scripts/preparar_revision_modelos.py` agregó `RESUMEN_OBJETIVO.json`, `revision_tecnica.csv` y `revision_candidatos_validos.csv`, con los hechos fuente junto a cada relación.

La prueba queda incompleta hasta que una persona competente revise `revision_candidatos_validos.csv`. Debe completar `correcto_0_o_1`, `util_0_a_2`, `afirmacion_no_respaldada_0_o_1` y un comentario cuando corresponda. Luego se cierra con:

```powershell
python scripts/cerrar_evaluacion_modelos.py `
  --rol-revisor "Responsable de mantenimiento"
```

El programa calcula el cumplimiento del umbral, pero no decide subjetivamente qué hallazgo es correcto.
