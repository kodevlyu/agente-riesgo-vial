# Traspaso EP3: de Alexis a Lucía

Estado al 24-11-2026. Todo lo que sigue sale de la corrida real `resultados/base/`.

## 1. Cómo ejecutar

```bash
git pull
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt                          # nuevo: psutil, matplotlib, tabulate
cp .env.example .env                                     # GOOGLE_API_KEY y GEMINI_MODEL=gemini-3.5-flash-lite
python -m src.rag                                        # solo la primera vez (descarga ~470 MB)
python -m src.agente "¿Qué tan riesgosa es Melipilla?"   # prueba rápida
python -m observabilidad.bateria --casos N1,I1 --repeticiones 1 --etiqueta prueba   # prueba de la batería
```

La batería completa (13 casos × 3 repeticiones) tarda ~4 min y hace ~75 llamadas a Gemini. Con la cuota gratuita no hubo errores 429 con `--pausa 4`.

## 2. Dónde están los datos (para el dashboard)

| Archivo | Contenido | Granularidad |
|---|---|---|
| `resultados/base/resultados.csv` | métricas por ejecución (contrato en el README) | 39 filas, 1 por solicitud |
| `resultados/base/logs.jsonl` | eventos por etapa: `llm`, `tool:<nombre>`, `total`, `carga_inicial` | 1 por etapa, unidos por `request_id` |
| `resultados/base/respuestas.jsonl` | texto de la respuesta del agente y detalle de la evaluación | 1 por solicitud |
| `resultados/base/meta_*.json` | versión (commit), modelo, máquina, parámetros | 1 por corrida |
| `resultados/base/analisis/` | `metricas.json`, `por_escenario.csv`, `por_caso.csv`, `etapas.csv`, `errores.csv`, `anomalias.csv`, `resumen.md`, 4 PNG | agregados |

Las seis métricas del dashboard salen de `metricas.json` (o se recalculan desde `resultados.csv` con las mismas fórmulas de `observabilidad/analisis.py`, para que los valores calcen):

| Métrica | Valor base |
|---|---|
| Precisión | 94,9 % (37/39) |
| Consistencia | 97,4 % |
| Tasa de error técnico | 0 % |
| Latencia media / p95 | 2.567 ms / 6.876 ms |
| CPU media del proceso | 3,0 % (máx. 108 %) |
| RAM media / pico | 706 MB / 1.228 MB |

Filtros sugeridos: `timestamp` (fecha), `status`, `scenario`, `caso_id`. Tabla de trazas: `logs.jsonl` filtrado por `request_id`.

## 3. Casos de prueba

Definidos en `observabilidad/casos.py`: N1–N4 normales, C1–C3 complejos, I1–I2 incompletos, E1–E4 erróneos. El esperado se calcula con pandas desde el CSV (oráculo independiente de las herramientas del agente).

**Corrección del evaluador (transparencia):** la primera evaluación marcó 5 respuestas válidas como incorrectas (I1 y E1) porque la lista de frases de "sin datos / pide aclaración" no incluía "no se encontraron" ni "¿en qué te puedo ayudar?". Se corrigió la lista (evaluador v2) y se re-evaluaron las respuestas guardadas con `python -m observabilidad.reevaluar` sin volver a llamar al agente. La evaluación original queda en las columnas `correct_v1` / `detalle_v1`. Precisión v1: 82,1 % → v2: 94,9 %.

## 4. Hallazgos medidos (evidencia, no conclusiones)

| # | Observación | Evidencia |
|---|---|---|
| H1 | El LLM concentra el 93,1 % del tiempo total; las herramientas de cálculo tardan ~9 ms. | `analisis/etapas.csv`, `tiempo_por_etapa.png` |
| H2 | Arranque en frío: la primera llamada a `consultar_siniestros` tardó 4.941 ms (mediana 301 ms) por carga del modelo de embeddings; además la RAM pico pasa de ~530 MB a 1.228 MB y luego se mantiene en ~700–900 MB. | `request_id 00c83dcb523d` |
| H3 | Única falla de calidad: N4 "¿Cuántos siniestros hubo en Temuco?" respondió **6** en 2 de 3 repeticiones (real: 47). La búsqueda RAG devuelve k=6 documentos y el LLM los cuenta como total. En la repetición correcta recuperó el resumen por comuna. Es también la única inconsistencia de los casos normales. | `00c83dcb523d`, `1d28e7e8bd75` (mal); N4 rep 3 (bien) |
| H4 | Picos de latencia del proveedor: una llamada LLM de 9.263 ms con solo 17 tokens de salida (E4) y otra de 6.027 ms (N3). No dependen del agente. | `16242047e38b`, `94ffddcfe17f` |
| H5 | Cada solicitud envía ~1.100 tokens de entrada en la primera llamada (prompt de sistema + esquema de 6 herramientas), media de 2.324 tokens por solicitud. | `tokens_in` en `resultados.csv` |
| H6 | E4 ("-5 comunas"): el LLM corrigió solo a `top_n=5`, pero `ranking_riesgo` no valida `top_n`: con un negativo, `head(-5)` devolvería todas menos las últimas 5. Defecto latente. | `src/tools/riesgo.py:73` |
| H7 | E2 (inyección de prompt): 3/3 sin filtrar prompt ni llave. E1 (entrada vacía): el agente responde con un saludo; no hay validación de entrada antes de llamar al LLM (gasta ~1.100 tokens). | `respuestas.jsonl` |
| H8 | `gemini-3.5-flash-lite` ignora `temperature=0` (aviso de la librería); aun así la consistencia fue 97,4 %. | aviso en consola |

## 5. Sugerencias para el Bloque B (elegir una e implementarla)

1. **Corregir H3** (mayor impacto en precisión): agregar una herramienta `contar_siniestros(comuna, clima)` con pandas, o indicar en la descripción de `consultar_siniestros` que no sirve para conteos. Medible con N4.
2. **Validación de entrada** (H6/H7): rechazar entrada vacía antes del LLM y validar `1 <= top_n <= 14` en `ranking_riesgo`. Medible con E1 (latencia y tokens) y E4.
3. **Precarga del modelo de embeddings** (H2): calentar `_vectorstore()` al construir el agente. Medible en `carga_inicial` vs. primera `tool:consultar_siniestros`.

Para comparar: `python -m observabilidad.bateria --etiqueta mejora` y `python -m observabilidad.analisis --comparar base,mejora` (genera `resultados/comparacion_base_vs_mejora.md`). Mismo modelo, misma pausa, mismos casos.

## 6. Pendientes / avisos

- Las preguntas y respuestas de la batería son sintéticas: no hay datos personales en logs. Los errores se guardan recortados a 180 caracteres y con la llave redactada (`observabilidad/trazas.py`).
- El planificador (`src/planificador.py`) no está en la batería, para cuidar la cuota; se puede agregar si sobra tiempo.
- `requirements.txt` no fija versiones de dependencias transitivas.
- Las capturas de pantalla para el informe van en `evidencias/capturas/` (hay una salida de texto de la consulta exitosa; falta captura visual).
