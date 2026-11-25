"""Análisis de una corrida de la batería: métricas, cuellos de botella y anomalías.

Uso:
    python -m observabilidad.analisis                 # analiza resultados/base/
    python -m observabilidad.analisis --etiqueta mejora
    python -m observabilidad.analisis --comparar base,mejora   # tabla antes/después

Escribe en resultados/<etiqueta>/analisis/: metricas.json, por_escenario.csv,
por_caso.csv, etapas.csv, errores.csv, anomalias.csv, resumen.md y gráficos PNG.

Definiciones (documentadas también en el README):
- Precisión     = ejecuciones correctas / ejecuciones evaluadas x 100 (una ejecución
                  con error cuenta como incorrecta). Se informa además la precisión
                  solo sobre ejecuciones sin error.
- Consistencia  = repeticiones equivalentes a la respuesta modal de su caso / repeticiones x 100.
                  Equivalencia = misma "firma" (veredicto, puntajes reales, comunas); ver casos.firma.
- Errores       = ejecuciones fallidas / totales x 100, clasificadas por error_type.
- Latencia      = duración total por solicitud y por etapa (ms): media, p50, p95, máx.
- CPU / RAM     = CPU % del proceso (100 % = 1 núcleo) y RSS en MB, medidos con psutil.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
ORDEN_ESC = ["normal", "complejo", "incompleto", "erroneo"]


def p95(s: pd.Series) -> float:
    return float(s.quantile(0.95)) if len(s) else float("nan")


def cargar(etiqueta: str):
    d = BASE / "resultados" / etiqueta
    res = pd.read_csv(d / "resultados.csv")
    logs = pd.read_json(d / "logs.jsonl", lines=True)
    return d, res, logs


def consistencia(res: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for caso, g in res.groupby("repeat_group"):
        moda = g["firma"].mode().iloc[0]
        eq = int((g["firma"] == moda).sum())
        filas.append({"caso_id": caso, "repeticiones": len(g), "equivalentes": eq,
                      "consistencia_pct": round(100 * eq / len(g), 1),
                      "firmas_distintas": g["firma"].nunique()})
    return pd.DataFrame(filas)


def metricas(res: pd.DataFrame, logs: pd.DataFrame) -> dict:
    ok = res[res["status"] == "ok"]
    cons = consistencia(res)
    carga = logs[logs["stage"] == "carga_inicial"]["duration_ms"]
    return {
        "ejecuciones": int(len(res)),
        "casos": int(res["caso_id"].nunique()),
        "precision_pct": round(100 * res["correct"].mean(), 1),
        "precision_sin_errores_pct": round(100 * ok["correct"].mean(), 1) if len(ok) else None,
        "consistencia_pct": round(100 * cons["equivalentes"].sum() / cons["repeticiones"].sum(), 1),
        "tasa_error_pct": round(100 * (res["status"] == "error").mean(), 1),
        "latencia_media_ms": round(res["latency_ms"].mean(), 1),
        "latencia_p50_ms": round(res["latency_ms"].median(), 1),
        "latencia_p95_ms": round(p95(res["latency_ms"]), 1),
        "latencia_max_ms": round(res["latency_ms"].max(), 1),
        "llm_share_pct": round(100 * res["llm_ms"].sum() / res["latency_ms"].sum(), 1),
        "tools_share_pct": round(100 * res["tools_ms"].sum() / res["latency_ms"].sum(), 1),
        "llamadas_llm_media": round(res["n_llm"].mean(), 2),
        "tokens_in_media": round(res["tokens_in"].mean(), 1),
        "tokens_out_media": round(res["tokens_out"].mean(), 1),
        "cpu_pct_media": round(res["cpu_pct"].mean(), 1),
        "cpu_pct_max": round(res["cpu_pct_max"].max(), 1),
        "ram_mb_media": round(res["ram_mb"].mean(), 1),
        "ram_peak_mb": round(res["ram_peak_mb"].max(), 1),
        "carga_inicial_ms": round(float(carga.iloc[0]), 1) if len(carga) else None,
    }


def por_grupo(res: pd.DataFrame, col: str) -> pd.DataFrame:
    g = res.groupby(col)
    t = pd.DataFrame({
        "n": g.size(),
        "precision_pct": (100 * g["correct"].mean()).round(1),
        "tasa_error_pct": (100 * g["status"].apply(lambda s: (s == "error").mean())).round(1),
        "latencia_media_ms": g["latency_ms"].mean().round(1),
        "latencia_p95_ms": g["latency_ms"].apply(p95).round(1),
        "llm_media": g["n_llm"].mean().round(2),
        "tools_media": g["n_tools"].mean().round(2),
        "tokens_in_media": g["tokens_in"].mean().round(0),
        "cpu_pct_media": g["cpu_pct"].mean().round(1),
        "ram_peak_mb": g["ram_peak_mb"].max().round(1),
    })
    return t


def etapas(logs: pd.DataFrame) -> pd.DataFrame:
    l = logs[~logs["stage"].isin(["total", "carga_inicial"])]
    total = logs.loc[logs["stage"] == "total", "duration_ms"].sum()
    g = l.groupby("stage")["duration_ms"]
    t = pd.DataFrame({
        "n": g.size(),
        "media_ms": g.mean().round(1),
        "p50_ms": g.median().round(1),
        "p95_ms": g.apply(p95).round(1),
        "max_ms": g.max().round(1),
        "suma_ms": g.sum().round(0),
        "pct_del_tiempo_total": (100 * g.sum() / total).round(1),
        "errores": l.groupby("stage")["status"].apply(lambda s: (s == "error").sum()),
        "sin_datos": l.groupby("stage")["status"].apply(lambda s: (s == "sin_datos").sum()),
    })
    return t.sort_values("suma_ms", ascending=False)


def errores(res: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    a = res[res["status"] == "error"].groupby("error_type").agg(
        ejecuciones=("request_id", "count"), ejemplo_request_id=("request_id", "first"))
    b = logs[(logs["status"] == "error") & (logs["stage"] != "total")].groupby("error_type").agg(
        eventos_etapa=("request_id", "count"))
    t = a.join(b, how="outer").fillna(0)
    # Respuestas incorrectas sin excepción: también son fallas (de calidad, no técnicas).
    malas = res[(res["status"] == "ok") & (res["correct"] == 0)]
    if len(malas):
        t.loc["respuesta_incorrecta", ["ejecuciones", "ejemplo_request_id"]] = [len(malas), malas["request_id"].iloc[0]]
    return t


def anomalias(res: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    filas = []
    lim = p95(res["latency_ms"])
    for _, r in res.iterrows():
        g = res[res["caso_id"] == r["caso_id"]]["latency_ms"]
        motivos = []
        if r["latency_ms"] > lim:
            motivos.append(f"latencia > p95 global ({lim:.0f} ms)")
        if len(g) > 1 and r["latency_ms"] > 2 * g.median():
            motivos.append(f"latencia > 2x mediana del caso ({g.median():.0f} ms)")
        if r["status"] == "error":
            motivos.append(f"error {r['error_type']}")
        elif not r["correct"]:
            motivos.append(f"incorrecta: {r['detalle']}")
        if motivos:
            filas.append({"request_id": r["request_id"], "caso_id": r["caso_id"],
                          "repeticion": r["repeticion"], "latency_ms": r["latency_ms"],
                          "n_llm": r["n_llm"], "herramientas": r["herramientas"],
                          "motivos": "; ".join(motivos)})
    # Arranque en frío: primera vez que se usa cada herramienta vs. su mediana.
    tl = logs[logs["stage"].str.startswith("tool:")].sort_values("timestamp")
    for stage, g in tl.groupby("stage"):
        if len(g) > 2 and g["duration_ms"].iloc[0] > 3 * g["duration_ms"].median():
            r = g.iloc[0]
            filas.append({"request_id": r["request_id"], "caso_id": r["caso_id"],
                          "repeticion": r["repeticion"], "latency_ms": r["duration_ms"],
                          "n_llm": None, "herramientas": stage,
                          "motivos": f"arranque en frío de {stage}: {r['duration_ms']:.0f} ms vs mediana {g['duration_ms'].median():.0f} ms"})
    return pd.DataFrame(filas)


def graficos(d: Path, res: pd.DataFrame, et: pd.DataFrame):
    out = d / "analisis"
    esc = [e for e in ORDEN_ESC if e in set(res["scenario"])]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot([res.loc[res["scenario"] == e, "latency_ms"] / 1000 for e in esc], tick_labels=esc)
    ax.set_ylabel("Latencia total (s)")
    ax.set_title("Latencia por escenario")
    fig.tight_layout(); fig.savefig(out / "latencia_por_escenario.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    et_plot = et.sort_values("suma_ms")
    ax.barh(et_plot.index, et_plot["suma_ms"] / 1000)
    ax.set_xlabel("Tiempo acumulado en la batería (s)")
    ax.set_title("Tiempo por etapa (cuello de botella)")
    fig.tight_layout(); fig.savefig(out / "tiempo_por_etapa.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    r = res.reset_index(drop=True)
    colores = r.apply(lambda x: "tab:red" if x["status"] == "error" else ("tab:green" if x["correct"] else "tab:orange"), axis=1)
    ax.scatter(r.index + 1, r["latency_ms"] / 1000, c=colores)
    ax.set_xlabel("Ejecución (orden)"); ax.set_ylabel("Latencia (s)")
    ax.set_title("Latencia por ejecución (verde correcta, naranja incorrecta, rojo error)")
    fig.tight_layout(); fig.savefig(out / "latencia_por_ejecucion.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    pc = res.groupby("caso_id")["correct"].mean() * 100
    ax.bar(pc.index, pc.values)
    ax.set_ylim(0, 105); ax.set_ylabel("Precisión (%)"); ax.set_title("Precisión por caso")
    fig.tight_layout(); fig.savefig(out / "precision_por_caso.png", dpi=150); plt.close(fig)


def md(df: pd.DataFrame) -> str:
    return df.to_markdown()


def analizar(etiqueta: str):
    d, res, logs = cargar(etiqueta)
    (d / "analisis").mkdir(exist_ok=True)
    m = metricas(res, logs)
    esc = por_grupo(res, "scenario").reindex([e for e in ORDEN_ESC if e in set(res["scenario"])])
    caso = por_grupo(res, "caso_id").join(consistencia(res).set_index("caso_id")[["consistencia_pct", "firmas_distintas"]])
    et = etapas(logs)
    err = errores(res, logs)
    an = anomalias(res, logs)

    a = d / "analisis"
    (a / "metricas.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    esc.to_csv(a / "por_escenario.csv"); caso.to_csv(a / "por_caso.csv")
    et.to_csv(a / "etapas.csv"); err.to_csv(a / "errores.csv"); an.to_csv(a / "anomalias.csv", index=False)
    graficos(d, res, et)

    resumen = [
        f"# Resumen de la corrida `{etiqueta}`", "",
        "Generado por `python -m observabilidad.analisis`. Datos reales de `resultados.csv` y `logs.jsonl`.", "",
        "## Métricas globales", "", md(pd.Series(m, name="valor").to_frame()), "",
        "## Por escenario", "", md(esc), "",
        "## Por caso (con consistencia)", "", md(caso), "",
        "## Latencia por etapa", "", md(et), "",
        "## Errores y fallas", "", md(err) if len(err) else "Sin errores.", "",
        "## Anomalías (con request_id para rastrear en logs.jsonl)", "",
        an.to_markdown(index=False) if len(an) else "Sin anomalías.", "",
    ]
    (a / "resumen.md").write_text("\n".join(resumen), encoding="utf-8")
    print("\n".join(resumen))


def comparar(a: str, b: str):
    _, ra, la = cargar(a)
    _, rb, lb = cargar(b)
    ma, mb = metricas(ra, la), metricas(rb, lb)
    t = pd.DataFrame({a: ma, b: mb})
    t["diferencia"] = [
        (round(y - x, 1) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else None)
        for x, y in zip(t[a], t[b])
    ]
    salida = BASE / "resultados" / f"comparacion_{a}_vs_{b}.md"
    salida.write_text(f"# Comparación {a} vs {b}\n\n" + t.to_markdown() + "\n", encoding="utf-8")
    print(t.to_markdown())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="base")
    ap.add_argument("--comparar", default="", help="dos etiquetas separadas por coma")
    args = ap.parse_args()
    if args.comparar:
        comparar(*args.comparar.split(","))
    else:
        analizar(args.etiqueta)
