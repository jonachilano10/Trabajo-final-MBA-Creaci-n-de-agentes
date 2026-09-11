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

GPT-5.4 Mini con `medium` es la configuración inicial. Nano sólo se adopta si iguala el resultado revisado; GPT-5.4 se reserva para casos ambiguos. Cada ejecución comparativa es paga y la página solicita confirmación.
