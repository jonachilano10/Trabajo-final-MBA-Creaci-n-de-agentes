# Evidencia de pruebas

Esta carpeta separa pruebas automáticas, mediciones reales, simulaciones económicas y controles de privacidad.

## Contenido

- `PRUEBAS_AUTOMATIZADAS.txt`: resultado de la suite de 13 pruebas, verificada nuevamente el 11/09/2026.
- `CONSUMO_REAL_CORRIDAS.csv`: tokens y costo reales informados por la API para las semanas 29 a 36.
- `MATRIZ_MODELOS.csv`: comparación económica homogénea de modelos y niveles con el volumen promedio observado.
- `CRITERIO_DE_EVALUACION.md`: protocolo para comparar calidad, consumo y costo.
- `PRUEBA_PRIVACIDAD_SEMANAS_31_Y_36.md`: prueba negativa deliberada con columnas personales, sin reproducir sus valores.
- `VALIDACION_BASE_VACIA.md`: inicialización independiente con cero semanas y verificación de aislamiento.
- `AUDITORIA_PRE_PUBLICACION.md`: revisión de secretos, datos personales y exclusiones antes de GitHub.
- `evidencia_reproducibilidad/`: corrida sintética desde una base vacía, con manifiesto, salida y reporte verificables.
- `comparacion_modelos_real/`: protocolo previo, resultados de API y planilla de revisión humana para AE-03.
- `RECONSTRUCCION_CORRIDAS_HISTORICAS.md`: límite de versión de las ocho corridas originales y corrección aplicada.
- `VERIFICACION_ENTREGA.json`: resultado del verificador único de estructura, corridas, pruebas y reproducción.

Las 13 pruebas cubren ventana histórica, autenticación, rechazo del modo público sin secretos, privacidad, archivado, base vacía, duplicados y salida estructurada. No se realizaron llamadas pagas para fabricar comparaciones entre modelos: `MATRIZ_MODELOS.csv` aplica tarifas distintas al mismo volumen promedio. Las ocho llamadas oficiales con GPT-5.4 Mini sí son mediciones reales y también se preservan dentro de cada corrida.

La prueba de modelos se considera completa únicamente cuando existan llamadas reales comparables y una revisión humana firmada. Hasta entonces, GPT-5.4 Mini es una elección provisional respaldada por ocho corridas válidas, no una superioridad demostrada frente a Nano.
