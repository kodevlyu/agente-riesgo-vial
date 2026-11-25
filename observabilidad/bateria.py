"""Batería de pruebas instrumentada del agente (EP3).

Uso:
    python -m observabilidad.bateria                       # 13 casos x 3 repeticiones -> resultados/mejorado/
    python -m observabilidad.bateria --etiqueta mejora     # misma batería, otra carpeta (comparar antes/después)
    python -m observabilidad.bateria --casos N1,I1 --repeticiones 1   # prueba rápida

Salidas en resultados/<etiqueta>/:
    resultados.csv   una fila por ejecución (contrato de datos)
    logs.jsonl       un evento por etapa (llm, tool:<nombre>, total, carga_inicial)
    respuestas.jsonl respuesta del agente y detalle de la evaluación (para auditar)
    meta.json        versión, modelo, máquina y parámetros de la corrida
"""

import argparse
import re
from src.seguridad import sanitizar_datos, redactar_secretos
import csv
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path
from uuid import uuid4

import psutil

warnings.filterwarnings("ignore", category=UserWarning)  # aviso de temperatura ignorada por el modelo

from src.agente import construir_agente, responder  # noqa: E402
from observabilidad.casos import CASOS, firma  # noqa: E402
from observabilidad.trazas import (  # noqa: E402
    MuestreadorRecursos,
    RegistroEventos,
    TrazadorEtapas,
    ahora_iso,
    clasificar_error,
    sanitizar_error,
)

BASE = Path(__file__).resolve().parent.parent
CAMPOS = [
    "request_id", "timestamp", "scenario", "caso_id", "repeat_group", "repeticion",
    "expected", "correct", "detalle", "firma", "status", "error_type",
    "latency_ms", "llm_ms", "tools_ms", "n_llm", "n_tools", "herramientas",
    "tokens_in", "tokens_out", "cpu_pct", "cpu_pct_max", "ram_mb", "ram_peak_mb",
    "version", "modelo",
]


def version_git() -> str:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=BASE, text=True).strip()
        sucio = subprocess.check_output(["git", "status", "--porcelain", "src"], cwd=BASE, text=True).strip()
        return commit + ("-mod" if sucio else "")
    except Exception:
        return "desconocida"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="mejorado")
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--casos", default="", help="IDs separados por coma; vacío = todos")
    ap.add_argument("--pausa", type=float, default=4.0, help="segundos entre solicitudes (cuota de Gemini)")
    ap.add_argument("--espera-429", type=float, default=60.0, help="segundos de espera tras un rate limit")
    args = ap.parse_args()

    casos = [c for c in CASOS if not args.casos or c.id in args.casos.split(",")]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", args.etiqueta) or args.etiqueta.lower() == "base":
        ap.error("Usa una etiqueta nueva y distinta de base.")
    if not casos or args.repeticiones < 1 or args.pausa < 0 or args.espera_429 < 0:
        ap.error("Parámetros de prueba inválidos.")
    salida = BASE / "resultados" / args.etiqueta
    salida.mkdir(parents=True, exist_ok=False)
    registro = RegistroEventos(salida / "logs.jsonl")
    version = version_git()
    modelo = os.getenv("GEMINI_MODEL", "")

    meta = {
        "etiqueta": args.etiqueta,
        "inicio": ahora_iso(),
        "version": version,
        "modelo": modelo,
        "python": sys.version.split()[0],
        "sistema": f"{platform.system()} {platform.release()} {platform.machine()}",
        "cpu_nucleos": psutil.cpu_count(),
        "ram_total_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "repeticiones": args.repeticiones,
        "casos": [c.id for c in casos],
        "pausa_s": args.pausa,
        "nota": "Cada ejecución usa un thread_id nuevo (sin memoria de corto plazo compartida). "
                "Las repeticiones se intercalan (ronda 1 de todos los casos, luego ronda 2...).",
    }

    # Etapa de carga inicial (construir grafo + cliente LLM). El modelo de embeddings
    # se carga de forma perezosa en la primera llamada a consultar_siniestros.
    rid_carga = f"init-{uuid4().hex[:8]}"
    t0 = time.perf_counter()
    agente = construir_agente()
    registro.escribir({
        "request_id": rid_carga, "timestamp": ahora_iso(), "stage": "carga_inicial",
        "duration_ms": round((time.perf_counter() - t0) * 1000, 1), "status": "ok",
        "error_type": "", "error": "", "scenario": "sistema", "caso_id": "", "repeticion": 0,
        "version": version,
    })

    ruta_csv = salida / "resultados.csv"
    nuevo = not ruta_csv.exists()
    f_csv = ruta_csv.open("a", newline="", encoding="utf-8")
    escritor = csv.DictWriter(f_csv, fieldnames=CAMPOS)
    if nuevo:
        escritor.writeheader()
    f_resp = (salida / "respuestas.jsonl").open("a", encoding="utf-8")

    total = len(casos) * args.repeticiones
    n = 0
    for rep in range(1, args.repeticiones + 1):
        for caso in casos:
            n += 1
            rid = uuid4().hex[:12]
            ctx = {"scenario": caso.escenario, "caso_id": caso.id, "repeticion": rep, "version": version}
            trazador = TrazadorEtapas(rid, ctx, registro)
            ts = ahora_iso()
            status, error_type, error, respuesta, herramientas = "ok", "", "", "", []

            t0 = time.perf_counter()
            with MuestreadorRecursos() as rec:
                try:
                    r = responder(caso.pregunta, sesion=f"bateria-{rid}", agente=agente, callbacks=[trazador])
                    respuesta, herramientas = r["respuesta"], r["herramientas"]
                except Exception as exc:  # se registra y la batería continúa
                    status, error_type, error = "error", clasificar_error(exc), sanitizar_error(exc)
            latencia = (time.perf_counter() - t0) * 1000

            if status == "ok":
                correcto, detalle = caso.evaluar(respuesta)
            else:
                correcto, detalle = False, f"sin respuesta ({error_type})"

            registro.escribir({
                "request_id": rid, "timestamp": ts, "stage": "total",
                "duration_ms": round(latencia, 1), "status": status, "error_type": error_type,
                "error": error, **ctx,
            })
            fila = {
                "request_id": rid, "timestamp": ts, "scenario": caso.escenario, "caso_id": caso.id,
                "repeat_group": caso.id, "repeticion": rep, "expected": caso.esperado,
                "correct": int(correcto), "detalle": detalle,
                "firma": firma(caso, respuesta, correcto) if status == "ok" else "error",
                "status": status, "error_type": error_type,
                "latency_ms": round(latencia, 1), "llm_ms": round(trazador.ms_llm, 1),
                "tools_ms": round(trazador.ms_tools, 1), "n_llm": trazador.n_llm,
                "n_tools": trazador.n_tools,
                "herramientas": ";".join(h["name"] for h in herramientas),
                "tokens_in": trazador.tokens_in, "tokens_out": trazador.tokens_out,
                **{k: rec.resultado[k] for k in ("cpu_pct", "cpu_pct_max", "ram_mb", "ram_peak_mb")},
                "version": version, "modelo": modelo,
            }
            escritor.writerow(sanitizar_datos(fila))
            f_csv.flush()
            f_resp.write(json.dumps(sanitizar_datos({
                "request_id": rid, "caso_id": caso.id, "repeticion": rep, "pregunta": caso.pregunta,
                "respuesta": respuesta, "herramientas": herramientas, "correct": correcto,
                "detalle": detalle, "status": status, "error_type": error_type, "error": error,
            }), ensure_ascii=False) + "\n")
            f_resp.flush()

            marca = "OK " if correcto else ("ERR" if status == "error" else "MAL")
            print(f"[{n:>2}/{total}] {marca} {caso.id} rep{rep} {latencia/1000:6.1f}s "
                  f"llm={trazador.n_llm} tools={trazador.n_tools} {error_type} {redactar_secretos(detalle)[:70]}", flush=True)

            time.sleep(args.espera_429 if error_type == "rate_limit" else args.pausa)

    f_csv.close()
    f_resp.close()
    meta["fin"] = ahora_iso()
    (salida / f"meta_{meta['inicio'][:19].replace(':', '')}.json").write_text(
        json.dumps(sanitizar_datos(meta), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nListo: {salida.relative_to(BASE)}")


if __name__ == "__main__":
    main()
