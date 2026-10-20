from datetime import datetime
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool

from src.rag import EmbeddingsLocales

BASE = Path(__file__).resolve().parent.parent.parent
MEMORIA_DIR = BASE / "chroma_memoria"


@lru_cache(maxsize=1)
def _store() -> Chroma:
    return Chroma(
        collection_name="memoria_largo_plazo",
        embedding_function=EmbeddingsLocales(),
        persist_directory=str(MEMORIA_DIR),
    )


def guardar_recuerdo_fn(texto: str, tipo: str = "preferencia") -> str:
    doc = Document(
        page_content=texto,
        metadata={"tipo": tipo, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")},
    )
    _store().add_documents([doc], ids=[str(uuid4())])
    return f"Recuerdo guardado ({tipo}): {texto}"


def buscar_recuerdos_fn(consulta: str, k: int = 3) -> list[str]:
    docs = _store().similarity_search(consulta, k=k)
    return [f"[{d.metadata.get('tipo')}, {d.metadata.get('fecha')}] {d.page_content}" for d in docs]


@tool
def guardar_recuerdo(texto: str, tipo: str = "preferencia") -> str:
    """Guarda en la memoria de largo plazo un dato que el usuario quiere que se
    recuerde en futuras conversaciones (una preferencia, una comuna de interés,
    una condición que le importa). Úsala solo cuando el usuario lo pida o cuente
    algo claramente duradero sobre sí mismo.
    Parámetros:
    - texto: el recuerdo, escrito como frase completa y clara.
    - tipo: 'preferencia', 'interes' o 'historial'.
    """
    return guardar_recuerdo_fn(texto, tipo)


@tool
def buscar_recuerdos(consulta: str) -> str:
    """Busca en la memoria de largo plazo recuerdos de conversaciones anteriores
    (preferencias, intereses, historial). Úsala cuando el usuario haga referencia
    a algo que dijo antes o cuando una preferencia suya pueda cambiar la respuesta.
    Parámetros:
    - consulta: tema a buscar en los recuerdos.
    """
    recuerdos = buscar_recuerdos_fn(consulta)
    if not recuerdos:
        return "No hay recuerdos guardados sobre eso."
    return "\n".join(f"- {r}" for r in recuerdos)


if __name__ == "__main__":
    print(guardar_recuerdo_fn("Prefiero reportes cortos y con foco en la comuna de Melipilla.", "preferencia"))
    print()
    print("Búsqueda: 'qué comuna le interesa al usuario'")
    for r in buscar_recuerdos_fn("qué comuna le interesa al usuario"):
        print("-", r)