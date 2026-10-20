import re
import unicodedata
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

BASE = Path(__file__).resolve().parent.parent.parent
OUTPUTS = BASE / "outputs"


def _slug(texto: str) -> str:
    sin_tildes = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")
    return slug[:50] or "reporte"


@tool
def guardar_reporte(titulo: str, contenido: str) -> str:
    """Guarda un reporte en un archivo Markdown dentro de la carpeta outputs/.
    Úsala solo cuando el usuario pida generar, guardar o escribir un reporte.
    Parámetros:
    - titulo: título corto del reporte.
    - contenido: cuerpo del reporte en formato Markdown, con los datos ya
      obtenidos de las otras herramientas (no inventes cifras).
    """
    OUTPUTS.mkdir(exist_ok=True)
    ahora = datetime.now()
    nombre = f"{_slug(titulo)}-{ahora:%Y%m%d-%H%M%S}.md"
    texto = (
        f"# {titulo}\n\n"
        f"_Generado el {ahora:%d-%m-%Y %H:%M}. Datos simulados con fines académicos._\n\n"
        f"{contenido}\n"
    )
    (OUTPUTS / nombre).write_text(texto, encoding="utf-8")
    return f"Reporte guardado en outputs/{nombre}"


if __name__ == "__main__":
    print(guardar_reporte.invoke({"titulo": "Prueba de reporte", "contenido": "- Funciona."}))