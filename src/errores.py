import os
import sys


def _cadena(exc: BaseException):
    """Recorre la excepción y sus causas encadenadas."""
    while exc is not None:
        yield exc
        exc = exc.__cause__ or exc.__context__


def _mensaje_para(exc: BaseException):
    texto = " ".join(str(e) for e in _cadena(exc))
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        return (
            "[ERROR] Se agotó la cuota de la API de Gemini (límite diario o por minuto).\n"
            "  - Si es por minuto: espera 1 minuto y vuelve a ejecutar.\n"
            "  - Si es diario: cambia GEMINI_MODEL en el archivo .env por otro modelo "
            "Flash disponible, o espera a que se renueve la cuota."
        )
    if "API key" in texto or "API_KEY" in texto or "PERMISSION_DENIED" in texto:
        return (
            "[ERROR] Problema con la llave de Gemini.\n"
            "  - Revisa que .env tenga GOOGLE_API_KEY con una llave válida.\n"
            "  - Si usas una cuenta institucional, prueba con una llave de un proyecto personal."
        )
    if "404" in texto and "model" in texto.lower():
        return (
            "[ERROR] El modelo configurado no existe o ya no está disponible.\n"
            "  - Revisa GEMINI_MODEL en el archivo .env."
        )
    return None


def instalar_manejo_errores():
    """Muestra un mensaje claro para fallas conocidas de la API.
    Para ver el error técnico completo, ejecutar antes: $env:DEBUG_TRACE = "1"
    """

    def _hook(tipo, exc, tb):
        mensaje = _mensaje_para(exc)
        if mensaje is None or os.getenv("DEBUG_TRACE") == "1":
            sys.__excepthook__(tipo, exc, tb)
            return
        print(f"\n{mensaje}", file=sys.stderr)

    sys.excepthook = _hook
    