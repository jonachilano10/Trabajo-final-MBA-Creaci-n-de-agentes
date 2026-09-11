# Contrato aplicado

La corrida utilizó las reglas vigentes documentadas en `Trabajo final/DECISIONES.md`, incluida la Decisión 007, y el módulo determinístico `Trabajo final/agente_mantenimiento`.

Controles centrales:

- sólo se consideran los 12 puentes P-MG autorizados;
- se filtra exclusivamente el período 24/08/2026-30/08/2026;
- se agregan horas, sin promediar disponibilidades de puentes;
- los Excel se leen y no se modifican;
- los valores históricos salen de SQLite y no son recalculados por el LLM;
- no se realizan proyecciones;
- las asociaciones de fallas son candidatos sujetos a revisión humana.
- la interpretación del LLM debe estar presente en la corrida terminada, pero es preliminar, no determinante y requiere siempre revisión humana.
