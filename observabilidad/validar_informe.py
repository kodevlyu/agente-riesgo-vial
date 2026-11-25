"""Valida las cifras del informe EP3 contra los archivos crudos de resultados/.

No usa analisis.py: recalcula cada valor con la biblioteca estándar desde
resultados.csv, logs.jsonl y respuestas.jsonl, y además cruza las fuentes entre
sí (CSV vs. logs). Cada fila compara el valor escrito en el informe con el
recalculado.

Uso: python -m observabilidad.validar_informe
Salida: resultados/validacion_informe.md (y resumen en consola)
"""

import csv
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
R = BASE / "resultados"


def cargar(etiqueta):
    d = R / etiqueta
    filas = list(csv.DictReader((d / "resultados.csv").open(encoding="utf-8")))
    for f in filas:
        for k in ("latency_ms", "llm_ms", "tools_ms", "cpu_pct", "ram_mb", "ram_peak_mb"):
            f[k] = float(f[k])
        for k in ("correct", "n_llm", "n_tools", "tokens_in", "tokens_out", "repeticion"):
            f[k] = int(float(f[k]))
    logs = [json.loads(l) for l in (d / "logs.jsonl").open(encoding="utf-8")]
    resp = {r["request_id"]: r for r in map(json.loads, (d / "respuestas.jsonl").open(encoding="utf-8"))}
    return filas, logs, resp


def p95(valores):
    # Percentil 95 con interpolación lineal (mismo criterio que pandas.quantile).
    v = sorted(valores)
    pos = 0.95 * (len(v) - 1)
    i = int(pos)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (pos - i)


def consistencia(filas):
    grupos = {}
    for f in filas:
        grupos.setdefault(f["repeat_group"], []).append(f["firma"])
    eq = sum(max(g.count(x) for x in set(g)) for g in grupos.values())
    return 100 * eq / len(filas)


def evento(logs, rid, stage, n=0):
    ev = [e for e in logs if e["request_id"] == rid and e["stage"] == stage]
    return ev[n] if len(ev) > n else None


filas_b, logs_b, resp_b = cargar("base")
filas_m, logs_m, resp_m = cargar("mejorado")
checks = []  # (sección, afirmación, valor en informe, valor recalculado, ok)


def chk(seccion, afirmacion, informe, real, tol=0.05):
    if isinstance(informe, (int, float)) and isinstance(real, (int, float)):
        ok = abs(informe - real) <= tol
        real_txt = f"{real:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        ok = informe == real
        real_txt = str(real)
    checks.append((seccion, afirmacion, str(informe), real_txt, ok))


for nombre, filas, logs in (("base", filas_b, logs_b), ("mejorado", filas_m, logs_m)):
    lat = [f["latency_ms"] for f in filas]
    esperado = {
        "base": dict(n=39, prec=94.9, cons=97.4, err=0.0, media=2567, p95=6876, max=10871, cpu=1.9, ram=706, tok=2324),
        "mejorado": dict(n=39, prec=97.4, cons=94.9, err=0.0, media=2497, p95=5777, max=13031, cpu=2.1, ram=318, tok=2643),
    }[nombre]
    s = f"2 · Comparación ({nombre})"
    chk(s, "Ejecuciones", esperado["n"], len(filas), 0)
    chk(s, "Precisión (%)", esperado["prec"], 100 * sum(f["correct"] for f in filas) / len(filas))
    chk(s, "Consistencia (%)", esperado["cons"], consistencia(filas))
    chk(s, "Errores técnicos (%)", esperado["err"], 100 * sum(f["status"] == "error" for f in filas) / len(filas))
    chk(s, "Latencia media (ms)", esperado["media"], statistics.mean(lat), 0.5)
    chk(s, "Latencia p95 (ms)", esperado["p95"], p95(lat), 0.5)
    chk(s, "Latencia máxima (ms)", esperado["max"], max(lat), 0.5)
    chk(s, "CPU mediana (%)", esperado["cpu"], statistics.median(f["cpu_pct"] for f in filas))
    chk(s, "RAM media (MB)", esperado["ram"], statistics.mean(f["ram_mb"] for f in filas), 0.5)
    chk(s, "Tokens de entrada por solicitud", esperado["tok"], statistics.mean(f["tokens_in"] for f in filas), 0.5)

    # Cruce entre fuentes: la latencia del CSV debe ser la del evento "total" del log,
    # y los tokens del CSV la suma de los eventos "llm" de esa solicitud.
    tot = {e["request_id"]: e["duration_ms"] for e in logs if e["stage"] == "total"}
    dif_lat = max(abs(f["latency_ms"] - tot[f["request_id"]]) for f in filas)
    chk(f"Cruce CSV–logs ({nombre})", "Máx. diferencia latencia CSV vs. evento total (ms)", 0, dif_lat, 0.2)
    dif_tok = max(abs(f["tokens_in"] - sum(e.get("tokens_in", 0) for e in logs if e["request_id"] == f["request_id"] and e["stage"] == "llm")) for f in filas)
    chk(f"Cruce CSV–logs ({nombre})", "Máx. diferencia tokens CSV vs. suma de eventos llm", 0, dif_tok, 0)
    # Las herramientas pueden correr en paralelo (C1, C3): se usa la unión de
    # intervalos (tiempo real ocupado), no la suma, para compararla con el total.
    def ocupado(rid):
        iv = sorted((datetime.fromisoformat(e["timestamp"]).timestamp() * 1000, e["duration_ms"])
                    for e in logs if e["request_id"] == rid and e["stage"] not in ("total", "carga_inicial"))
        total, fin = 0.0, float("-inf")
        for ini, dur in iv:
            total += max(0.0, ini + dur - max(ini, fin))
            fin = max(fin, ini + dur)
        return total
    exceso = max(ocupado(f["request_id"]) - f["latency_ms"] for f in filas)
    chk(f"Cruce CSV–logs ({nombre})", "El tiempo ocupado por las etapas no supera la latencia total", True, exceso <= 2.0)
    paralelas = sum(1 for f in filas if len({e["timestamp"] for e in logs if e["request_id"] == f["request_id"] and e["stage"].startswith("tool:")}) < sum(1 for e in logs if e["request_id"] == f["request_id"] and e["stage"].startswith("tool:")) or ocupado(f["request_id"]) + 1 < sum(e["duration_ms"] for e in logs if e["request_id"] == f["request_id"] and e["stage"] not in ("total", "carga_inicial")))
    checks.append((f"Cruce CSV–logs ({nombre})", "Solicitudes con herramientas en paralelo (informativo)", "—", str(paralelas), True))

# Participación del LLM en el tiempo total
for nombre, logs, valor in (("base", logs_b, 93.1), ("mejorado", logs_m, 92.7)):
    total = sum(e["duration_ms"] for e in logs if e["stage"] == "total")
    llm = sum(e["duration_ms"] for e in logs if e["stage"] == "llm")
    chk("3 · Hallazgos", f"H1: % del tiempo en el LLM ({nombre})", valor, 100 * llm / total)

calc = [e["duration_ms"] for e in logs_b if e["stage"] in ("tool:calcular_riesgo_comuna", "tool:ranking_riesgo")]
chk("3 · Hallazgos", "H1: herramientas de cálculo, media (ms) ~10", 10, statistics.mean(calc), 1.0)
e = evento(logs_b, "16242047e38b", "llm")
chk("3 · Hallazgos", "H1: pico LLM 16242047e38b (ms)", 9263, e["duration_ms"], 0.5)
chk("3 · Hallazgos", "H1: tokens de salida del pico", 17, e["tokens_out"], 0)

rid = "00c83dcb523d"
chk("3 · Trazabilidad", f"{rid}: primera llamada LLM (ms)", 1401, evento(logs_b, rid, "llm")["duration_ms"], 0.5)
chk("3 · Trazabilidad", f"{rid}: búsqueda RAG (ms)", 4941, evento(logs_b, rid, "tool:consultar_siniestros")["duration_ms"], 0.5)
chk("3 · Trazabilidad", f"{rid}: la respuesta dice 6 siniestros", True, bool(re.search(r"\b6 siniestros", resp_b[rid]["respuesta"])))
temuco = sum(1 for f in csv.DictReader((BASE / "data" / "siniestros.csv").open(encoding="utf-8")) if f["comuna"] == "Temuco")
chk("3 · Trazabilidad", "Siniestros reales en Temuco (CSV de datos)", 47, temuco, 0)

n4b = [f for f in filas_b if f["caso_id"] == "N4"]
chk("3 · Hallazgos", "H2: N4 base correctas", "1 de 3", f"{sum(f['correct'] for f in n4b)} de {len(n4b)}")
rag = sorted(e["duration_ms"] for e in logs_b if e["stage"] == "tool:consultar_siniestros")
chk("3 · Hallazgos", "H3: mediana de consultar_siniestros (ms)", 301, statistics.median(rag), 0.5)
chk("3 · Hallazgos", "H3: RAM pico base (MB)", 1228, max(f["ram_peak_mb"] for f in filas_b), 0.5)
e1b = [f for f in filas_b if f["caso_id"] == "E1"]
chk("3 · Hallazgos", "H4: E1 base sí llamaba al LLM (llamadas por ejecución)", 1, min(f["n_llm"] for f in e1b), 0)
f = next(f for f in filas_m if f["request_id"] == "e7431b03a8fb")
chk("3 · Hallazgos", "H5: e7431b03a8fb es E3 con 5 llamadas al LLM", "E3 / 5", f"{f['caso_id']} / {f['n_llm']}")
chk("3 · Hallazgos", "H5: e7431b03a8fb latencia (s)", 13.0, f["latency_ms"] / 1000, 0.1)

e12 = [f for f in filas_m if f["caso_id"] in ("E1", "E2")]
chk("4 · Seguridad", "E1 y E2 correctas (mejorado)", "6 de 6", f"{sum(f['correct'] for f in e12)} de {len(e12)}")
chk("4 · Seguridad", "E1 y E2 latencia máxima < 3 ms", True, max(f["latency_ms"] for f in e12) < 3)
chk("4 · Seguridad", "E1 y E2 sin llamadas al LLM", True, all(f["n_llm"] == 0 for f in e12))
e4 = [resp_m[f["request_id"]]["respuesta"] for f in filas_m if f["caso_id"] == "E4"]
rechaza = sum(bool(re.search(r"negativ|positiv|mayor a cero", r, re.I)) for r in e4)
chk("4 · Seguridad", "E4: rechaza el -5 (revisión del texto de las 3 respuestas)", "3 de 3", f"{rechaza} de {len(e4)}")
n4m = [f for f in filas_m if f["caso_id"] == "N4"]
chk("4 · Mejora", "N4 mejorado correctas", "3 de 3", f"{sum(f['correct'] for f in n4m)} de {len(n4m)}")
chk("4 · Escalabilidad", "Tokens de entrada mejorado ~2.600", 2600, statistics.mean(f["tokens_in"] for f in filas_m), 60)
rag_m = [e["duration_ms"] for e in logs_m if e["stage"] == "tool:consultar_siniestros"]
chk("4 · Escalabilidad", "Carga de embeddings ~5 s (máx. consultar_siniestros, s)", 5.0, max(rag_m) / 1000, 0.8)
chk("4 · Escalabilidad", "RAM al cargar ~1,1 GB (pico mejorado, GB)", 1.1, max(f["ram_peak_mb"] for f in filas_m) / 1024, 0.06)

cpu_media_m = statistics.mean(f["cpu_pct"] for f in filas_m)
chk("2 · Comparación", "CPU media mejorado descartada (%)", 18.6, cpu_media_m)
b_csv = list(csv.DictReader((R / "base" / "resultados.csv").open(encoding="utf-8")))
cambios = sum(r["correct"] != r["correct_v1"] for r in b_csv)
chk("2 · Corrección del evaluador", "Respuestas re-evaluadas en la base", 5, cambios, 0)
f = next(f for f in filas_m if f["request_id"] == "39ac067d9e22")
chk("2 · Comparación", "39ac067d9e22 es la única incorrecta del mejorado (E4)", "E4 / 1", f"{f['caso_id']} / {sum(1 - x['correct'] for x in filas_m)}")
chk("5 · Resultados", "Ejecuciones totales sin error técnico", 78, sum(f["status"] == "ok" for f in filas_b + filas_m), 0)

# Ninguna credencial en resultados/
patron = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")
fugas = [p.name for p in R.rglob("*") if p.is_file() and p.suffix in (".csv", ".jsonl", ".json", ".md") and patron.search(p.read_text(encoding="utf-8", errors="ignore"))]
chk("4 · Seguridad", "Archivos de resultados/ con una clave API", 0, len(fugas), 0)

ok = sum(c[4] for c in checks)
lineas = [
    "# Validación de las cifras del informe EP3", "",
    "Generado por `python -m observabilidad.validar_informe`. Recalcula cada valor desde `resultados.csv`, "
    "`logs.jsonl` y `respuestas.jsonl` sin usar `analisis.py`, y cruza las fuentes entre sí.", "",
    f"**Resultado: {ok} de {len(checks)} comprobaciones coinciden.**", "",
    "| Sección | Afirmación | Informe | Recalculado | ¿Coincide? |", "| --- | --- | --- | --- | --- |",
] + [f"| {s} | {a} | {i} | {r} | {'sí' if k else '**NO**'} |" for s, a, i, r, k in checks]
(R / "validacion_informe.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(f"{ok}/{len(checks)} comprobaciones coinciden")
for s, a, i, r, k in checks:
    if not k:
        print("NO COINCIDE:", s, "|", a, "| informe:", i, "| real:", r)
