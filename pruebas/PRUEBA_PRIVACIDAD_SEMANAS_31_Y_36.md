# Prueba de rechazo de información confidencial

**Fecha de ejecución:** 9 de septiembre de 2026  
**Tipo de prueba:** caso negativo deliberado con archivos reales de prueba  
**Resultado:** aprobado

## Objetivo

Comprobar que el agente rechaza una carga antes de calcular, guardar en SQLite o invocar al LLM cuando un Excel contiene columnas con información personal.

Los archivos fueron incluidos deliberadamente por el responsable del proyecto para verificar el control. Se conservaron sin modificaciones. Este documento no reproduce ni almacena ninguno de los valores confidenciales detectados.

## Entradas y resultados

| Semana | Archivo | SHA-256 | Ubicación detectada | Resultado esperado | Resultado observado |
|---|---|---|---|---|---|
| 31/2026 | `31-Notificaciones semana 31.XLSX` | `36BB78090C6C9EA00D6E07CDF94A98337E4664F160BF9695AF36C7FD2AA62F50` | Hoja `Sheet1`, columnas O (`Nombre del empleado`) y Q (`Número de personal`) | Rechazar el lote | Rechazado antes del análisis |
| 36/2026 | `36-Notificaciones semana 36.XLSX` | `8D2E1DD6C4F2FCF1A234F4F71CEA5CCBBFE3C31E5C9231D008675BA1E4C3497A` | Hoja `Sheet1`, columnas O (`Nombre del empleado`) y Q (`Número de personal`) | Rechazar el lote | Rechazado antes del análisis |
| 36/2026 | `Avisos semana 36.XLSX` | `8CB1A5F33520E62C52374AA6A3BECE48F534C7492340ECBB9AECC9BC45380C02` | Hoja `Sheet1`, columna X (`Nombre y Apellido`) | Rechazar el lote | Rechazado antes del análisis |

## Mensaje esperado

> Los archivos contienen información confidencial, no se ejecutará el análisis.

El sistema agregó la ubicación de cada hallazgo para permitir la depuración sin mostrar el contenido de las celdas.

## Controles verificados

- Se revisaron todas las hojas, columnas y valores antes del cálculo.
- No se generó un informe de disponibilidad para las semanas rechazadas.
- No se insertaron las semanas 31 ni 36 en SQLite.
- No se invocó al LLM.
- No se modificaron los Excel ni el ZIP originales.
- Las semanas 29, 30 y 32 del mismo lote superaron el control de privacidad y la validación estructural preliminar; tampoco se guardaron durante esta prueba.

## Uso posterior

Estos archivos deben conservarse como evidencia negativa y no deben publicarse en GitHub. Para procesar las semanas 31 y 36 se requieren copias depuradas, sin las columnas identificadas. Las copias depuradas y los originales de prueba deben tener nombres distintos para evitar una carga accidental.
