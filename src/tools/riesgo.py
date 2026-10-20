from functools import lru_cache

import pandas as pd
from langchain_core.tools import tool

from src.rag import CSV

CLIMAS_VALIDOS = ["Despejado", "Lluvia", "Niebla", "Nublado"]


@lru_cache(maxsize=1)
def _datos() -> pd.DataFrame:
    return pd.read_csv(CSV)


def _tabla_riesgo(clima: str = "") -> pd.DataFrame:
    df = _datos()
    if clima:
        df = df[df["clima"].str.lower() == clima.lower()]
    if df.empty:
        return pd.DataFrame()
    t = df.groupby(["comuna", "region"]).agg(
        siniestros=("id_siniestro", "count"),
        fallecidos=("fallecidos", "sum"),
        graves=("lesionados_graves", "sum"),
    )
    t["bruto"] = 10 * t["fallecidos"] + 3 * t["graves"] + t["siniestros"]
    t["puntaje"] = (100 * t["bruto"] / t["bruto"].max()).round(1)
    t["nivel"] = t["puntaje"].apply(
        lambda p: "ALTO" if p >= 66 else ("MEDIO" if p >= 33 else "BAJO")
    )
    return t.reset_index().sort_values("puntaje", ascending=False)


@tool
def calcular_riesgo_comuna(comuna: str, clima: str = "") -> str:
    """Calcula el puntaje de riesgo vial (0 a 100) y el nivel (ALTO, MEDIO o BAJO)
    de una comuna. Usa la fórmula: 10*fallecidos + 3*lesionados graves + 1*siniestros,
    comparada con la comuna más riesgosa.
    Parámetros:
    - comuna: nombre exacto de la comuna (ej: 'Melipilla').
    - clima: opcional; 'Despejado', 'Lluvia', 'Niebla' o 'Nublado' para calcular
      el riesgo solo con siniestros ocurridos bajo ese clima.
    """
    t = _tabla_riesgo(clima)
    if t.empty:
        return f"No hay datos para el clima '{clima}'. Climas válidos: {CLIMAS_VALIDOS}."
    fila = t[t["comuna"].str.lower() == comuna.lower()]
    if fila.empty:
        return f"No hay datos de la comuna '{comuna}' con ese filtro."
    f = fila.iloc[0]
    puesto = int(t.reset_index(drop=True).index[t["comuna"] == f["comuna"]][0]) + 1
    cond = f"con clima {clima}" if clima else "en todas las condiciones"
    return (
        f"Riesgo de {f['comuna']} ({cond}): puntaje {f['puntaje']}/100, nivel {f['nivel']}. "
        f"Puesto {puesto} de {len(t)} comunas. Detalle: {int(f['siniestros'])} siniestros, "
        f"{int(f['fallecidos'])} fallecidos, {int(f['graves'])} lesionados graves."
    )


@tool
def ranking_riesgo(top_n: int = 5, clima: str = "") -> str:
    """Entrega el ranking de las comunas con mayor riesgo vial, ordenadas por puntaje.
    Parámetros:
    - top_n: cuántas comunas mostrar (por defecto 5).
    - clima: opcional; 'Despejado', 'Lluvia', 'Niebla' o 'Nublado' para filtrar.
    """
    t = _tabla_riesgo(clima)
    if t.empty:
        return f"No hay datos para el clima '{clima}'. Climas válidos: {CLIMAS_VALIDOS}."
    cond = f"con clima {clima}" if clima else "en todas las condiciones"
    lineas = [f"Ranking de riesgo vial ({cond}):"]
    for i, (_, f) in enumerate(t.head(top_n).iterrows(), start=1):
        lineas.append(
            f"{i}. {f['comuna']}: {f['puntaje']}/100 ({f['nivel']}), "
            f"{int(f['siniestros'])} siniestros, {int(f['fallecidos'])} fallecidos"
        )
    return "\n".join(lineas)


if __name__ == "__main__":
    print(ranking_riesgo.invoke({"top_n": 5}))
    print()
    print(ranking_riesgo.invoke({"top_n": 5, "clima": "Lluvia"}))
    print()
    print(calcular_riesgo_comuna.invoke({"comuna": "Melipilla"}))