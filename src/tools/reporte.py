import re
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.tools import tool
from src.seguridad import contiene_credenciales

BASE = Path(__file__).resolve().parent.parent.parent
OUTPUTS = BASE / 'outputs'
MAX_TITULO = 150
MAX_CONTENIDO = 30000


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', sin_tildes.lower()).strip('-')[:50] or 'reporte'


@tool
def guardar_reporte(titulo: str, contenido: str) -> str:
    """Guarda un reporte Markdown en outputs/ solo si el usuario lo solicita.

    titulo: título corto del reporte.
    contenido: datos verificados en Markdown, sin credenciales ni datos secretos.
    """
    titulo = titulo.strip()
    contenido = contenido.strip()
    if not titulo or not contenido:
        return 'Consulta inválida: el título y el contenido son obligatorios.'
    if len(titulo) > MAX_TITULO or len(contenido) > MAX_CONTENIDO:
        return 'Consulta inválida: el reporte supera los límites de tamaño.'
    if contiene_credenciales(titulo) or contiene_credenciales(contenido):
        return 'Consulta inválida: el reporte contiene posibles credenciales.'
    if any(ord(c) < 32 for c in titulo):
        return 'Consulta inválida: el título contiene caracteres de control.'
    try:
        OUTPUTS.mkdir(exist_ok=True)
        if OUTPUTS.resolve() != BASE.resolve() / 'outputs':
            return 'Consulta inválida: directorio de reportes no autorizado.'
        ahora = datetime.now()
        nombre = f'{_slug(titulo)}-{ahora:%Y%m%d-%H%M%S}-{uuid4().hex[:12]}.md'
        destino = OUTPUTS / nombre
        if destino.resolve().parent != OUTPUTS.resolve():
            return 'Consulta inválida: ruta de reporte no autorizada.'
        texto = (f'# {titulo}\n\n'
                 f'_Generado el {ahora:%d-%m-%Y %H:%M}. Datos simulados con fines académicos._\n\n'
                 f'{contenido}\n')
        with destino.open('x', encoding='utf-8') as archivo:
            archivo.write(texto)
        return f'Reporte guardado en outputs/{nombre}'
    except OSError:
        return 'No se encontraron condiciones seguras para guardar el reporte.'


if __name__ == '__main__':
    print(guardar_reporte.invoke({'titulo': 'Prueba de reporte', 'contenido': '- Funciona.'}))
