import os
import sys
import traceback
from src.seguridad import redactar_secretos


def _cadena(exc):
    vistos = set()
    while exc is not None and id(exc) not in vistos:
        vistos.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _mensaje_para(exc):
    texto = " ".join(str(e) for e in _cadena(exc)).lower()
    if "billing" in texto or "free tier is not available" in texto:
        return "[ERROR] El proyecto Gemini no tiene acceso al nivel gratuito o requiere facturación. Revisa la elegibilidad del proyecto."
    if "429" in texto or "resource_exhausted" in texto:
        return "[ERROR] Cuota de Gemini agotada. Revisa los límites y espera antes de reintentar."
    if any(x in texto for x in ("api key", "api_key", "permission_denied", "401", "403")):
        return "[ERROR] Acceso a Gemini denegado. Revisa la clave y los permisos del proyecto."
    if "404" in texto and "model" in texto:
        return "[ERROR] Modelo no disponible. Revisa GEMINI_MODEL."
    return None


def instalar_manejo_errores():
    def _hook(tipo, exc, tb):
        if isinstance(exc, KeyboardInterrupt):
            print("Interrumpido por el usuario.", file=sys.stderr)
            return
        mensaje = _mensaje_para(exc)
        if os.getenv("DEBUG_TRACE") == "1":
            print(redactar_secretos("".join(traceback.format_exception(tipo, exc, tb))), file=sys.stderr)
        else:
            print(mensaje or f"[ERROR] {tipo.__name__}: {redactar_secretos(str(exc))[:180]}", file=sys.stderr)
    sys.excepthook = _hook
