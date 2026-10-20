from functools import lru_cache

from langchain_core.tools import tool

from src.rag import obtener_vectorstore


@lru_cache(maxsize=1)
def _vectorstore():
    # Se carga una sola vez (cargar el modelo de embeddings es lento).
    return obtener_vectorstore()


@tool
def consultar_siniestros(consulta: str, comuna: str = "") -> str:
    """Busca siniestros viales y resúmenes por comuna en la base de datos de Chile.
    Úsala para responder preguntas sobre cuántos siniestros hubo, sus causas,
    el clima, la ruta o las víctimas.
    Parámetros:
    - consulta: la pregunta o tema a buscar (ej: 'exceso de velocidad con lluvia').
    - comuna: opcional; nombre exacto de la comuna para filtrar (ej: 'Melipilla').
    """
    filtro = {"comuna": comuna} if comuna else None
    resultados = _vectorstore().similarity_search(consulta, k=6, filter=filtro)
    if not resultados:
        return "No se encontraron siniestros para esa consulta."
    return "\n".join(f"- {d.page_content}" for d in resultados)


if __name__ == "__main__":
    print(
        consultar_siniestros.invoke(
            {"consulta": "exceso de velocidad con lluvia", "comuna": "Melipilla"}
        )
    )