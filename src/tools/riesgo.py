
import unicodedata
from functools import lru_cache

import pandas as pd
from langchain_core.tools import tool

from src.rag import CSV


CLIMAS_VALIDOS = [
    "Despejado",
    "Lluvia",
    "Niebla",
    "Nublado",
]


# ==========================================
# CARGA Y NORMALIZACIÓN DE DATOS
# ==========================================

@lru_cache(maxsize=1)
def _datos() -> pd.DataFrame:
    return pd.read_csv(CSV)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize(
        "NFKD",
        texto.strip().casefold()
    )

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def _validar_clima(clima: str):
    clima = clima.strip()

    if not clima:
        return "", ""

    for valido in CLIMAS_VALIDOS:

        if _normalizar(clima) == _normalizar(valido):
            return valido, ""

    return "", (
        f"Consulta inválida: clima '{clima}'. "
        f"Climas válidos: {', '.join(CLIMAS_VALIDOS)}."
    )


# ==========================================
# CÁLCULO DEL RIESGO VIAL
# ==========================================

def _tabla_riesgo(clima: str = "") -> pd.DataFrame:

    df = _datos()

    if clima:

        df = df[
            df["clima"].map(_normalizar)
            == _normalizar(clima)
        ]

    if df.empty:
        return pd.DataFrame()

    t = df.groupby(["comuna", "region"]).agg(
        siniestros=("id_siniestro", "count"),
        fallecidos=("fallecidos", "sum"),
        graves=("lesionados_graves", "sum"),
    )

    # Se conserva la fórmula original del proyecto.
    t["bruto"] = (
        10 * t["fallecidos"]
        + 3 * t["graves"]
        + t["siniestros"]
    )

    maximo = t["bruto"].max()

    if maximo > 0:

        t["puntaje"] = (
            100 * t["bruto"] / maximo
        ).round(1)

    else:

        t["puntaje"] = 0.0

    t["nivel"] = t["puntaje"].apply(
        lambda p: (
            "ALTO"
            if p >= 66
            else ("MEDIO" if p >= 33 else "BAJO")
        )
    )

    return (
        t.reset_index()
        .sort_values("puntaje", ascending=False)
        .reset_index(drop=True)
    )


# ==========================================
# HERRAMIENTA: RIESGO POR COMUNA
# ==========================================

@tool
def calcular_riesgo_comuna(
    comuna: str,
    clima: str = ""
) -> str:
    """Calcula el puntaje de riesgo vial de una comuna.

    El puntaje va de 0 a 100 y el nivel puede ser
    ALTO, MEDIO o BAJO.

    Fórmula:
    10*fallecidos + 3*lesionados graves + siniestros,
    comparada con la comuna más riesgosa.

    Parámetros:
    - comuna: nombre de la comuna.
    - clima: opcional; Despejado, Lluvia,
      Niebla o Nublado.
    """

    comuna = comuna.strip()

    if not comuna:

        return (
            "Consulta inválida: "
            "debes indicar una comuna."
        )

    if len(comuna) > 100:

        return (
            "Consulta inválida: "
            "el nombre de la comuna es demasiado largo."
        )

    clima, error = _validar_clima(clima)

    if error:
        return error

    t = _tabla_riesgo(clima)

    if t.empty:

        return (
            f"No hay datos para el clima '{clima}'. "
            f"Climas válidos: {', '.join(CLIMAS_VALIDOS)}."
        )

    fila = t[
        t["comuna"].map(_normalizar)
        == _normalizar(comuna)
    ]

    if fila.empty:

        return (
            f"No hay datos de la comuna "
            f"'{comuna}' con ese filtro."
        )

    f = fila.iloc[0]

    puesto = int(fila.index[0]) + 1

    cond = (
        f"con clima {clima}"
        if clima
        else "en todas las condiciones"
    )

    return (
        f"Riesgo de {f['comuna']} ({cond}): "
        f"puntaje {f['puntaje']}/100, "
        f"nivel {f['nivel']}. "
        f"Puesto {puesto} de {len(t)} comunas. "
        f"Detalle: {int(f['siniestros'])} siniestros, "
        f"{int(f['fallecidos'])} fallecidos, "
        f"{int(f['graves'])} lesionados graves. "
        "Datos simulados con fines académicos."
    )


# ==========================================
# HERRAMIENTA: RANKING DE RIESGO
# ==========================================

@tool
def ranking_riesgo(
    top_n: int = 5,
    clima: str = ""
) -> str:
    """Entrega el ranking de comunas con mayor riesgo.

    Parámetros:
    - top_n: cantidad positiva de comunas a mostrar.
      Por defecto 5.
    - clima: opcional; Despejado, Lluvia,
      Niebla o Nublado.

    No admite cantidades negativas ni cero.
    """

    if top_n <= 0:

        return (
            "Consulta inválida: la cantidad del ranking "
            "debe ser un número entero mayor que cero."
        )

    clima, error = _validar_clima(clima)

    if error:
        return error

    t = _tabla_riesgo(clima)

    if t.empty:

        return (
            f"No hay datos para el clima '{clima}'. "
            f"Climas válidos: {', '.join(CLIMAS_VALIDOS)}."
        )

    disponibles = len(t)

    cantidad = min(top_n, disponibles)

    cond = (
        f"con clima {clima}"
        if clima
        else "en todas las condiciones"
    )

    lineas = [
        f"Ranking de riesgo vial ({cond}):"
    ]

    if top_n > disponibles:

        lineas.append(
            f"Se solicitaron {top_n} posiciones, "
            f"pero solo existen {disponibles} "
            "comunas con datos disponibles."
        )

    for i, (_, f) in enumerate(
        t.head(cantidad).iterrows(),
        start=1
    ):

        lineas.append(
            f"{i}. {f['comuna']}: "
            f"{f['puntaje']}/100 ({f['nivel']}), "
            f"{int(f['siniestros'])} siniestros, "
            f"{int(f['fallecidos'])} fallecidos"
        )

    lineas.append(
        "Datos simulados con fines académicos."
    )

    return "\n".join(lineas)


# ==========================================
# PRUEBAS DESDE TERMINAL
# ==========================================

if __name__ == "__main__":

    print(ranking_riesgo.invoke({"top_n": 5}))

    print()

    print(
        ranking_riesgo.invoke({
            "top_n": 5,
            "clima": "Lluvia"
        })
    )

    print()

    print(
        calcular_riesgo_comuna.invoke({
            "comuna": "Melipilla"
        })
    )
