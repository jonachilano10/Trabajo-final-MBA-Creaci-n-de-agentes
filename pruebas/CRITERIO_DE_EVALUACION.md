# Criterio para comparar modelos

## Objetivo

Elegir el modelo más chico que realice correctamente la interpretación preliminar de fallas, sin permitir que modifique cálculos.

## Procedimiento

1. Seleccionar una semana almacenada y revisada por una persona competente.
2. Ejecutar el mismo contexto con cada modelo y nivel desde la sección económica.
3. Registrar automáticamente tokens y costo en SQLite.
4. Comparar los hallazgos con la evidencia y el dictamen humano.
5. Marcar relaciones correctas, falsas, omitidas y afirmaciones no respaldadas.
6. Adoptar el modelo de menor costo que alcance el umbral técnico definido.

## Umbral fijado antes de probar

La configuración debe completar ambas semanas de prueba con JSON válido, cero avisos o métricas inventados, cero afirmaciones causales no respaldadas, al menos 80 % de relaciones correctas y una utilidad media mínima de 1,5 sobre 2 según revisión humana.

GPT-5.4 Mini con `medium` es la configuración inicial y todavía provisional. Nano sólo se adopta si supera el umbral; GPT-5.4 se reserva para casos ambiguos salvo que los resultados demuestren otra necesidad. Cada ejecución comparativa es paga y requiere confirmación explícita.

La implementación reproducible se encuentra en `scripts/comparar_modelos.py` y el diseño completo en `pruebas/comparacion_modelos_real/README.md`. La matriz económica simulada no sustituye esta evaluación de calidad.
