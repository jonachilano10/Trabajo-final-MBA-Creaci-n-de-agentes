# Reconstrucción de las corridas históricas

## Alcance

Se revisaron las ocho corridas oficiales, semanas 29 a 36 de 2026. Todas contienen entradas identificadas, prompts, validación, resultados, contexto, hallazgos, consumo, costo y reporte.

## Limitación encontrada

La versión o commit del código no fue almacenada en el momento de esas ejecuciones. Por ese motivo no corresponde asignarles retrospectivamente el commit actual. Los SHA-256 de los Excel demuestran identidad, pero un tercero sin acceso autorizado a las fuentes no puede reconstruir esas semanas exactas.

## Corrección aplicada

- Se preservaron intactas como evidencia cronológica.
- Se creó la versión `1.1.0` con manifiesto automático de entorno, versión, código y artefactos.
- Se agregó una reproducción pública con Excel sintéticos y base vacía.
- Las corridas nuevas incorporarán esta trazabilidad automáticamente.

Este tratamiento prioriza honestidad y auditabilidad sobre una apariencia artificial de completitud.
