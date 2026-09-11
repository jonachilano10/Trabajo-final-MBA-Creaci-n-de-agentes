# Comparación real de modelos

Esta carpeta recibirá la prueba paga necesaria para cerrar **AE-03**. No contiene resultados simulados presentados como reales.

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

El programa generará `resultados_api.json`, `MANIFIESTO.json` y `evaluacion_humana.csv`. La prueba queda incompleta hasta que una persona competente revise el CSV, firme y redacte la conclusión. El programa no decide subjetivamente qué hallazgo es correcto.
