# Análisis económico del agente

Fecha de cierre: 11/09/2026. Moneda: USD. Los importes no incluyen impuestos, conversión a pesos ni servicios de infraestructura. Las tarifas aplicadas son las registradas por el programa con fecha efectiva 08/09/2026.

## Consumo real de las corridas oficiales

Las semanas 29 a 36 se ejecutaron con `gpt-5.4-mini` y razonamiento `medium`. Python guardó el uso informado por la API; no se reconstruyeron ni inventaron tokens.

La tabla también se entrega como `pruebas/CONSUMO_REAL_CORRIDAS.csv`; la comparación homogénea completa por modelo y nivel está en `pruebas/MATRIZ_MODELOS.csv`.

| Semana | Entrada | Entrada cacheada | Salida | Razonamiento incluido en salida | Total | Costo |
|---:|---:|---:|---:|---:|---:|---:|
| 29 | 3.907 | 0 | 3.488 | 2.246 | 7.395 | US$ 0,018626 |
| 30 | 6.126 | 0 | 5.408 | 3.875 | 11.534 | US$ 0,028930 |
| 31 | 10.175 | 0 | 8.053 | 6.691 | 18.228 | US$ 0,043870 |
| 32 | 13.567 | 0 | 7.234 | 5.244 | 20.801 | US$ 0,042728 |
| 33 | 17.733 | 0 | 5.840 | 3.595 | 23.573 | US$ 0,039580 |
| 34 | 21.104 | 0 | 7.690 | 6.038 | 28.794 | US$ 0,050433 |
| 35 | 24.147 | 0 | 5.072 | 3.554 | 29.219 | US$ 0,040934 |
| 36 | 25.547 | 25.344 | 6.736 | 4.973 | 32.283 | US$ 0,032365 |
| **Total** | **122.306** | **25.344** | **49.521** | **36.216** | **171.827** | **US$ 0,297467** |

La entrada cacheada es parte de los tokens de entrada, no se suma nuevamente al total. Los tokens de razonamiento están incluidos en los tokens de salida.

## Costo operativo observado

- Costo promedio por corrida: **US$ 0,037183**.
- Corrida real de menor costo: **US$ 0,018626**.
- Corrida real de mayor costo: **US$ 0,050433**.
- Proyección a 52 corridas anuales usando el promedio observado: **US$ 1,9335 por año**.
- Promedio mensual equivalente: **US$ 0,1611**.

La proyección anual es un escenario económico, no una proyección de disponibilidad ni de fallas. El costo real puede variar por longitud de los textos, cantidad de eventos, caché, modelo y nivel de razonamiento.

## Comparación homogénea de modelos

Para comparar modelos se usa el volumen promedio observado: 15.288 tokens de entrada y 6.190 tokens de salida por corrida, sin suponer caché. De esta forma todos reciben la misma carga de trabajo.

| Modelo | Entrada por 1 M | Salida por 1 M | Corrida comparable | Ahorro frente a GPT-5.4 | 52 corridas/año |
|---|---:|---:|---:|---:|---:|
| GPT-5.4 | US$ 2,50 | US$ 15,00 | US$ 0,131073 | 0,0 % | US$ 6,8158 |
| GPT-5.4 Mini | US$ 0,75 | US$ 4,50 | US$ 0,039322 | 70,0 % | US$ 2,0447 |
| GPT-5.4 Nano | US$ 0,20 | US$ 1,25 | US$ 0,010795 | 91,8 % | US$ 0,5614 |

La fórmula es:

```text
costo = entrada no cacheada × tarifa de entrada
      + entrada cacheada × tarifa cacheada
      + salida total × tarifa de salida
```

Todos los términos se dividen por un millón. La aplicación conserva las tarifas junto con cada ejecución para que el cálculo sea auditable.

## Elección provisional de modelo y nivel

Se eligió **GPT-5.4 Mini con razonamiento medium** porque Python realiza los cálculos, validaciones y filtros; el LLM sólo relaciona textos y redacta hallazgos preliminares. En las ocho semanas produjo salidas estructuradas válidas, por lo que un modelo mayor no quedó justificado para el flujo normal.

GPT-5.4 puede reservarse para revisar casos ambiguos. GPT-5.4 Nano promete menor costo, pero no debe adoptarse sin ejecutar una comparación de calidad sobre casos históricos revisados por una persona. Los niveles de razonamiento no tienen una tarifa unitaria distinta, aunque pueden modificar la cantidad de tokens de salida consumidos.

La elección se declara **provisional** hasta completar el benchmark real definido en `pruebas/comparacion_modelos_real/README.md`. La comparación previa demuestra costo, pero no equivalencia de calidad. El programa `scripts/comparar_modelos.py` ejecuta Nano, Mini y GPT-5.4 sobre las mismas semanas sin alterar la base oficial, registra tokens y prepara una evaluación humana. No se presentan resultados simulados como si fueran ejecuciones reales.

## Control del crecimiento

El LLM recibe la semana actual y como máximo las seis semanas anteriores. SQLite y los gráficos mantienen todo el historial, pero el contexto semántico no crece indefinidamente. La semana 36 ya ejercitó la ventana completa y consumió 25.547 tokens de entrada; además aprovechó 25.344 tokens cacheados, por lo que su costo fue menor que el de algunas semanas con menos contexto.

## Almacenamiento y costo total de propiedad

La medición de la entrega final, con ocho semanas, arrojó:

| Componente | Tamaño medido | Promedio aproximado |
|---|---:|---:|
| SQLite | 315.392 bytes | 39.424 bytes/semana |
| Archivos de las ocho corridas | 1.820.565 bytes | 227.571 bytes/semana |
| Entorno completo de ejecución | 2.961.685 bytes | 370.211 bytes/semana |

Una extrapolación lineal conservadora de SQLite más archivos de corrida es inferior a 15 MB por año. Reservar 25 MB anuales contempla metadatos adicionales, crecimiento irregular y holgura. Es una estimación de almacenamiento, no una proyección de disponibilidad.

| Escenario anual | Hosting y respaldo | Dominio | API estimada | TCO de infraestructura |
|---|---:|---:|---:|---:|
| Académico/local en equipo existente | US$ 0 incremental | US$ 0 | US$ 1,93 | **US$ 1,93** |
| Web pequeña, supuesto bajo | US$ 6/mes | US$ 15/año | US$ 1,93 | **US$ 88,93/año** |
| Web pequeña, supuesto conservador | US$ 12/mes | US$ 20/año | US$ 1,93 | **US$ 165,93/año** |

Los valores de hosting y dominio son supuestos de presupuesto, no cotizaciones de un proveedor. Deben reemplazarse por la oferta vigente al desplegar. No incluyen horas de revisión humana, soporte, impuestos ni integración corporativa. Para el volumen actual, el costo dominante no es SQLite ni el LLM, sino mantener un backend persistente, seguro y respaldado.

## Límites del análisis

- Los costos de API corresponden exclusivamente al uso registrado; hosting y dominio son escenarios presupuestarios declarados.
- No se incluyen soporte, impuestos ni horas de revisión humana.
- La proyección anual supone una corrida semanal y el promedio de las ocho observadas.
- Los precios pueden cambiar; las futuras ejecuciones deben utilizar la tarifa vigente y conservar su fecha efectiva.
- La calidad no se infiere del costo: los hallazgos continúan sujetos a revisión humana obligatoria.
