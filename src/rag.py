import shutil
from pathlib import Path

import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "data" / "siniestros.csv"
CHROMA_DIR = BASE / "chroma_db"
COLECCION = "siniestros"
MODELO_EMB = "paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingsLocales(Embeddings):
    """Embeddings multilingües locales (no consumen cuota de la API)."""

    def __init__(self, nombre: str = MODELO_EMB):
        self.modelo = SentenceTransformer(nombre)

    def embed_documents(self, textos):
        return self.modelo.encode(textos, normalize_embeddings=True).tolist()

    def embed_query(self, texto):
        return self.modelo.encode([texto], normalize_embeddings=True)[0].tolist()


def _docs_siniestros(df: pd.DataFrame):
    docs, ids = [], []
    for _, f in df.iterrows():
        texto = (
            f"Siniestro {f.id_siniestro} ocurrido el {f.fecha} a las {f.hora} "
            f"en la comuna de {f.comuna} (región {f.region}), ruta {f.ruta}. "
            f"Tipo: {f.tipo}. Causa: {f.causa}. Clima: {f.clima}. "
            f"Lesionados graves: {f.lesionados_graves}. Fallecidos: {f.fallecidos}."
        )
        docs.append(
            Document(
                page_content=texto,
                metadata={
                    "tipo_doc": "siniestro",
                    "comuna": f.comuna,
                    "region": f.region,
                    "clima": f.clima,
                    "fecha": f.fecha,
                    "lesionados_graves": int(f.lesionados_graves),
                    "fallecidos": int(f.fallecidos),
                },
            )
        )
        ids.append(f"sin-{f.id_siniestro}")
    return docs, ids


def _docs_resumen_comunas(df: pd.DataFrame):
    docs, ids = [], []
    for comuna, g in df.groupby("comuna"):
        total = len(g)
        pct_lluvia = round(100 * (g["clima"] == "Lluvia").mean(), 1)
        causa_top = g["causa"].value_counts().idxmax()
        texto = (
            f"Resumen de la comuna de {comuna} (región {g['region'].iloc[0]}): "
            f"{total} siniestros registrados, {int(g['fallecidos'].sum())} fallecidos, "
            f"{int(g['lesionados_graves'].sum())} lesionados graves. "
            f"Causa más frecuente: {causa_top}. "
            f"{pct_lluvia}% de los siniestros ocurrieron con lluvia."
        )
        docs.append(
            Document(
                page_content=texto,
                metadata={"tipo_doc": "resumen_comuna", "comuna": comuna},
            )
        )
        ids.append(f"res-{comuna}")
    return docs, ids


def construir_indice():
    df = pd.read_csv(CSV)
    docs1, ids1 = _docs_siniestros(df)
    docs2, ids2 = _docs_resumen_comunas(df)
    docs, ids = docs1 + docs2, ids1 + ids2

    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    vs = Chroma.from_documents(
        documents=docs,
        embedding=EmbeddingsLocales(),
        collection_name=COLECCION,
        persist_directory=str(CHROMA_DIR),
        ids=ids,
    )
    print(f"Indexados {len(docs)} chunks ({len(docs1)} siniestros + {len(docs2)} resúmenes).")
    return vs


def obtener_vectorstore():
    return Chroma(
        collection_name=COLECCION,
        embedding_function=EmbeddingsLocales(),
        persist_directory=str(CHROMA_DIR),
    )


if __name__ == "__main__":
    vs = construir_indice()
    print("\nPrueba de búsqueda: 'accidentes por exceso de velocidad en Melipilla'\n")
    for d in vs.similarity_search("accidentes por exceso de velocidad en Melipilla", k=3):
        print("-", d.page_content, "\n")