
from functools import lru_cache
import unicodedata

import pandas as pd
from langchain_core.tools import tool

from src.rag import CSV, obtener_vectorstore


@lru_cache(maxsize=1)
def _vectorstore():
    # Carga única del modelo de embeddings.
    return obtener_vectorstore()


@lru_cache(maxsize=1)
def _datos():
    return pd.read_csv(CSV)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.strip().casefold())
    return "".join(
        caracter for caracter in texto
        if not unicodedata.combining(caracter)
    )


@tool
def consultar_estadisticas(
    comuna: str,
    clima: str = "",
    causa: str = ""
) -> str:
    """Calcula estadísticas exactas desde el conjunto completo de datos.

    Usar para cantidades totales de siniestros, causas más frecuentes,
    fallecidos y lesionados graves.

    Parámetros:
    - comuna: nombre de la comuna.
    - clima: filtro opcional por condición climática.
    - causa: filtro opcional por causa del siniestro.
    """

    if not comuna.strip():
        return "Consulta inválida: debes indicar una comuna."

    df = _datos()

    datos = df[
        df["comuna"].map(_normalizar) == _normalizar(comuna)
    ]

    if datos.empty:
        return f"No hay datos de la comuna '{comuna}'."

    nombre_comuna = datos["comuna"].iloc[0]

    if clima.strip():
        climas_validos = df["clima"].dropna().unique()

        if _normalizar(clima) not in [
            _normalizar(c) for c in climas_validos
        ]:
            return (
                f"Consulta inválida: clima '{clima}'. "
                f"Climas válidos: {', '.join(sorted(climas_validos))}."
            )

        datos = datos[
            datos["clima"].map(_normalizar) == _normalizar(clima)
        ]

    if causa.strip():
        causas_validas = df["causa"].dropna().unique()

        if _normalizar(causa) not in [
            _normalizar(c) for c in causas_validas
        ]:
            return (
                f"Consulta inválida: causa '{causa}'. "
                f"Causas válidas: {', '.join(sorted(causas_validas))}."
            )

        datos = datos[
            datos["causa"].map(_normalizar) == _normalizar(causa)
        ]

    total = len(datos)

    if total == 0:
        return (
            f"Estadísticas exactas de {nombre_comuna}: "
            "0 siniestros registrados con los filtros indicados. "
            "Datos simulados con fines académicos."
        )

    fallecidos = int(datos["fallecidos"].sum())
    graves = int(datos["lesionados_graves"].sum())

    causas = datos["causa"].value_counts()
    max_causa = causas.max()

    causas_frecuentes = ", ".join(
        causas[causas == max_causa].index.tolist()
    )

    porcentaje_lluvia = round(
        100 * (datos["clima"] == "Lluvia").mean(), 1
    )

    filtros = []

    if clima.strip():
        filtros.append(f"clima: {clima}")

    if causa.strip():
        filtros.append(f"causa: {causa}")

    condiciones = (
        ", ".join(filtros)
        if filtros
        else "todas las condiciones"
    )

    return (
        f"Estadísticas exactas de {nombre_comuna} "
        f"({condiciones}):\n"
        f"- Total de siniestros: {total}\n"
        f"- Fallecidos: {fallecidos}\n"
        f"- Lesionados graves: {graves}\n"
        f"- Causa más frecuente: {causas_frecuentes}\n"
        f"- Frecuencia de cada causa principal: {max_causa}\n"
        f"- Porcentaje de siniestros con lluvia: "
        f"{porcentaje_lluvia}%\n"
        "Fuente: conjunto completo de datos siniestros.csv.\n"
        "Datos simulados con fines académicos."
    )


@tool
def consultar_siniestros(
    consulta: str,
    comuna: str = ""
) -> str:
    """Busca ejemplos y documentos relevantes mediante RAG.

    Úsala para búsquedas semánticas, detalles de siniestros
    y recuperación de información contextual.

    Los documentos recuperados NO representan el total
    de siniestros registrados.

    Para cantidades exactas y estadísticas utiliza
    consultar_estadisticas.
    """

    if not consulta.strip():
        return "Consulta inválida: la búsqueda no puede estar vacía."

    filtro = None

    if comuna.strip():
        df = _datos()

        comunas = df[
            df["comuna"].map(_normalizar) == _normalizar(comuna)
        ]

        if comunas.empty:
            return f"No hay datos de la comuna '{comuna}'."

        filtro = {"comuna": comunas["comuna"].iloc[0]}

    resultados = _vectorstore().similarity_search(
        consulta,
        k=6,
        filter=filtro
    )

    if not resultados:
        return "No se encontraron siniestros para esa consulta."

    encabezado = (
        f"Documentos recuperados: {len(resultados)}.\n"
        "Esta cantidad NO corresponde al total de siniestros.\n"
    )

    return encabezado + "\n".join(
        f"- {d.page_content}" for d in resultados
    )


if __name__ == "__main__":
    print(
        consultar_estadisticas.invoke(
            {"comuna": "Temuco"}
        )
    )
