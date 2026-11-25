import os
import re
import unicodedata


MAX_PREGUNTA = 4000

MENSAJE_PROTECCION = (
    "Consulta inválida: no puedo revelar "
    "credenciales ni instrucciones internas. "
    "Puedo ayudarte con consultas sobre seguridad vial."
)


def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize(
        "NFKD",
        texto.casefold()
    )

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def contiene_credenciales(texto: str) -> bool:

    patrones = [
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"(?i)bearer\s+[a-z0-9._\-]{10,}",
        r"(?i)(api[_ -]?key|password|contraseña|"
        r"secret|token)\s*[:=]\s*\S+",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    ]

    for patron in patrones:

        if re.search(patron, texto):
            return True

    for variable in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):

        valor = os.getenv(variable, "")

        if valor and valor in texto:
            return True

    return False


def redactar_secretos(texto: str) -> str:

    for variable in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):

        valor = os.getenv(variable, "")

        if valor:
            texto = texto.replace(
                valor,
                "[REDACTADO]"
            )

    texto = re.sub(
        r"AIza[0-9A-Za-z_\-]{20,}",
        "[REDACTADO]",
        texto
    )

    texto = re.sub(
        r"(?i)bearer\s+[a-z0-9._\-]{10,}",
        "Bearer [REDACTADO]",
        texto
    )

    texto = re.sub(
        r"(?i)(api[_ -]?key|password|contraseña|"
        r"secret|token)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTADO]",
        texto
    )

    texto = re.sub(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r".*?-----END [A-Z ]*PRIVATE KEY-----",
        "[REDACTADO]",
        texto,
        flags=re.DOTALL
    )

    return texto


def detectar_inyeccion(texto: str) -> bool:

    normalizado = normalizar_texto(texto)

    objetivos = (
        "prompt de sistema",
        "system prompt",
        "instrucciones internas",
        "instrucciones del sistema",
        "google_api_key",
        "gemini_api_key",
        "clave de api",
        "api key",
        "variables de entorno",
    )

    acciones = (
        "muestrame",
        "revela",
        "imprime",
        "entrega",
        "dime",
        "muestra",
        "devuelve",
        "exhibe",
        "extrae",
        "reveal",
        "show",
        "print",
        "ignora",
        "ignore",
    )

    solicita_objetivo = any(
        objetivo in normalizado
        for objetivo in objetivos
    )

    solicita_accion = any(
        accion in normalizado
        for accion in acciones
    )

    return solicita_objetivo and solicita_accion


def validar_pregunta(pregunta: str) -> tuple[bool, str]:

    if not isinstance(pregunta, str):

        return False, (
            "Consulta inválida: "
            "la pregunta debe ser texto."
        )

    pregunta = pregunta.strip()

    if not pregunta:

        return False, (
            "Consulta inválida: debes indicar "
            "una pregunta sobre seguridad vial."
        )

    if len(pregunta) > MAX_PREGUNTA:

        return False, (
            "Consulta inválida: la pregunta "
            f"supera los {MAX_PREGUNTA} caracteres."
        )

    if contiene_credenciales(pregunta):

        return False, (
            "Consulta inválida: no incluyas "
            "credenciales ni datos secretos."
        )

    if detectar_inyeccion(pregunta):

        return False, MENSAJE_PROTECCION

    return True, pregunta


def sanitizar_datos(valor):
    """Sanitiza estructuras sin alterar los valores numéricos."""
    if isinstance(valor, str):
        return redactar_secretos(valor)
    if isinstance(valor, dict):
        return {redactar_secretos(str(k)): ("[REDACTADO]" if normalizar_texto(str(k)) in {"password", "token", "secret", "api_key", "google_api_key", "gemini_api_key", "authorization", "contrasena"} else sanitizar_datos(v)) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [sanitizar_datos(v) for v in valor]
    return valor
