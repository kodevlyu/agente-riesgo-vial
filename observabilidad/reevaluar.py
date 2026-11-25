"""Re-evalúa una corrida con la versión actual de las reglas, sin volver a llamar al agente.

Uso: python -m observabilidad.reevaluar --etiqueta base

Lee respuestas.jsonl (respuestas reales guardadas), recalcula correct/detalle/firma
y reescribe resultados.csv. La evaluación anterior se conserva en las columnas
correct_v1 y detalle_v1 para documentar qué cambió y por qué.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from observabilidad.casos import CASOS, VERSION_EVALUADOR, firma

BASE = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="base")
    args = ap.parse_args()
    d = BASE / "resultados" / args.etiqueta
    res = pd.read_csv(d / "resultados.csv")
    resp = {r["request_id"]: r for r in map(json.loads, (d / "respuestas.jsonl").open(encoding="utf-8"))}
    casos = {c.id: c for c in CASOS}

    if "correct_v1" not in res:
        res["correct_v1"], res["detalle_v1"] = res["correct"], res["detalle"]
    for i, fila in res.iterrows():
        r = resp[fila["request_id"]]
        if fila["status"] != "ok":
            continue
        caso = casos[fila["caso_id"]]
        ok, det = caso.evaluar(r["respuesta"])
        res.loc[i, ["correct", "detalle", "firma"]] = [int(ok), det, firma(caso, r["respuesta"], ok)]
    res["evaluador"] = VERSION_EVALUADOR
    res.to_csv(d / "resultados.csv", index=False)

    cambios = res[res["correct"] != res["correct_v1"]]
    print(f"Re-evaluadas {len(res)} ejecuciones con evaluador {VERSION_EVALUADOR}. Cambios: {len(cambios)}")
    print(cambios[["request_id", "caso_id", "repeticion", "correct_v1", "correct", "detalle"]].to_string(index=False))
