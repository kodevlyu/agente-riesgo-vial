# Validación de las cifras del informe EP3

Generado por `python -m observabilidad.validar_informe`. Recalcula cada valor desde `resultados.csv`, `logs.jsonl` y `respuestas.jsonl` sin usar `analisis.py`, y cruza las fuentes entre sí.

**Resultado: 56 de 56 comprobaciones coinciden.**

| Sección | Afirmación | Informe | Recalculado | ¿Coincide? |
| --- | --- | --- | --- | --- |
| 2 · Comparación (base) | Ejecuciones | 39 | 39,0 | sí |
| 2 · Comparación (base) | Precisión (%) | 94.9 | 94,9 | sí |
| 2 · Comparación (base) | Consistencia (%) | 97.4 | 97,4 | sí |
| 2 · Comparación (base) | Errores técnicos (%) | 0.0 | 0,0 | sí |
| 2 · Comparación (base) | Latencia media (ms) | 2567 | 2.567,5 | sí |
| 2 · Comparación (base) | Latencia p95 (ms) | 6876 | 6.876,2 | sí |
| 2 · Comparación (base) | Latencia máxima (ms) | 10871 | 10.870,6 | sí |
| 2 · Comparación (base) | CPU mediana (%) | 1.9 | 1,9 | sí |
| 2 · Comparación (base) | RAM media (MB) | 706 | 706,2 | sí |
| 2 · Comparación (base) | Tokens de entrada por solicitud | 2324 | 2.323,9 | sí |
| Cruce CSV–logs (base) | Máx. diferencia latencia CSV vs. evento total (ms) | 0 | 0,0 | sí |
| Cruce CSV–logs (base) | Máx. diferencia tokens CSV vs. suma de eventos llm | 0 | 0,0 | sí |
| Cruce CSV–logs (base) | El tiempo ocupado por las etapas no supera la latencia total | True | 1,0 | sí |
| Cruce CSV–logs (base) | Solicitudes con herramientas en paralelo (informativo) | — | 6 | sí |
| 2 · Comparación (mejorado) | Ejecuciones | 39 | 39,0 | sí |
| 2 · Comparación (mejorado) | Precisión (%) | 97.4 | 97,4 | sí |
| 2 · Comparación (mejorado) | Consistencia (%) | 94.9 | 94,9 | sí |
| 2 · Comparación (mejorado) | Errores técnicos (%) | 0.0 | 0,0 | sí |
| 2 · Comparación (mejorado) | Latencia media (ms) | 2497 | 2.496,7 | sí |
| 2 · Comparación (mejorado) | Latencia p95 (ms) | 5777 | 5.777,2 | sí |
| 2 · Comparación (mejorado) | Latencia máxima (ms) | 13031 | 13.030,9 | sí |
| 2 · Comparación (mejorado) | CPU mediana (%) | 2.1 | 2,1 | sí |
| 2 · Comparación (mejorado) | RAM media (MB) | 318 | 318,4 | sí |
| 2 · Comparación (mejorado) | Tokens de entrada por solicitud | 2643 | 2.643,3 | sí |
| Cruce CSV–logs (mejorado) | Máx. diferencia latencia CSV vs. evento total (ms) | 0 | 0,0 | sí |
| Cruce CSV–logs (mejorado) | Máx. diferencia tokens CSV vs. suma de eventos llm | 0 | 0,0 | sí |
| Cruce CSV–logs (mejorado) | El tiempo ocupado por las etapas no supera la latencia total | True | 1,0 | sí |
| Cruce CSV–logs (mejorado) | Solicitudes con herramientas en paralelo (informativo) | — | 6 | sí |
| 3 · Hallazgos | H1: % del tiempo en el LLM (base) | 93.1 | 93,1 | sí |
| 3 · Hallazgos | H1: % del tiempo en el LLM (mejorado) | 92.7 | 92,7 | sí |
| 3 · Hallazgos | H1: herramientas de cálculo, media (ms) ~10 | 10 | 9,4 | sí |
| 3 · Hallazgos | H1: pico LLM 16242047e38b (ms) | 9263 | 9.262,8 | sí |
| 3 · Hallazgos | H1: tokens de salida del pico | 17 | 17,0 | sí |
| 3 · Trazabilidad | 00c83dcb523d: primera llamada LLM (ms) | 1401 | 1.401,1 | sí |
| 3 · Trazabilidad | 00c83dcb523d: búsqueda RAG (ms) | 4941 | 4.940,8 | sí |
| 3 · Trazabilidad | 00c83dcb523d: la respuesta dice 6 siniestros | True | 1,0 | sí |
| 3 · Trazabilidad | Siniestros reales en Temuco (CSV de datos) | 47 | 47,0 | sí |
| 3 · Hallazgos | H2: N4 base correctas | 1 de 3 | 1 de 3 | sí |
| 3 · Hallazgos | H3: mediana de consultar_siniestros (ms) | 301 | 301,0 | sí |
| 3 · Hallazgos | H3: RAM pico base (MB) | 1228 | 1.228,0 | sí |
| 3 · Hallazgos | H4: E1 base sí llamaba al LLM (llamadas por ejecución) | 1 | 1,0 | sí |
| 3 · Hallazgos | H5: e7431b03a8fb es E3 con 5 llamadas al LLM | E3 / 5 | E3 / 5 | sí |
| 3 · Hallazgos | H5: e7431b03a8fb latencia (s) | 13.0 | 13,0 | sí |
| 4 · Seguridad | E1 y E2 correctas (mejorado) | 6 de 6 | 6 de 6 | sí |
| 4 · Seguridad | E1 y E2 latencia máxima < 3 ms | True | 1,0 | sí |
| 4 · Seguridad | E1 y E2 sin llamadas al LLM | True | 1,0 | sí |
| 4 · Seguridad | E4: rechaza el -5 (revisión del texto de las 3 respuestas) | 3 de 3 | 3 de 3 | sí |
| 4 · Mejora | N4 mejorado correctas | 3 de 3 | 3 de 3 | sí |
| 4 · Escalabilidad | Tokens de entrada mejorado ~2.600 | 2600 | 2.643,3 | sí |
| 4 · Escalabilidad | Carga de embeddings ~5 s (máx. consultar_siniestros, s) | 5.0 | 5,8 | sí |
| 4 · Escalabilidad | RAM al cargar ~1,1 GB (pico mejorado, GB) | 1.1 | 1,1 | sí |
| 2 · Comparación | CPU media mejorado descartada (%) | 18.6 | 18,6 | sí |
| 2 · Corrección del evaluador | Respuestas re-evaluadas en la base | 5 | 5,0 | sí |
| 2 · Comparación | 39ac067d9e22 es la única incorrecta del mejorado (E4) | E4 / 1 | E4 / 1 | sí |
| 5 · Resultados | Ejecuciones totales sin error técnico | 78 | 78,0 | sí |
| 4 · Seguridad | Archivos de resultados/ con una clave API | 0 | 0,0 | sí |
