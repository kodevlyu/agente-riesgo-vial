"""Instrumentación del agente: trazas por etapa, recursos y errores sanitizados.

- TrazadorEtapas: callback de LangChain que mide cada llamada al LLM y a cada
  herramienta (etapa, duración, estado, tokens). Todas las etapas de una
  solicitud comparten el mismo request_id.
- MuestreadorRecursos: hilo que muestrea CPU % y RAM (RSS) del proceso cada
  100 ms mientras dura la solicitud (psutil).
- sanitizar_error / clasificar_error: nunca se registra la llave ni texto
  largo del proveedor; solo un tipo de error y un mensaje recortado.
"""

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from src.seguridad import redactar_secretos, sanitizar_datos

import psutil
from langchain_core.callbacks import BaseCallbackHandler

PROCESO = psutil.Process(os.getpid())


def ahora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


# --------------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------------
def _cadena(exc: BaseException):
    while exc is not None:
        yield exc
        exc = exc.__cause__ or exc.__context__


def clasificar_error(exc: BaseException) -> str:
    texto = " ".join(f"{type(e).__name__} {e}" for e in _cadena(exc))
    bajo = texto.lower()
    if "billing" in bajo or "free tier is not available" in bajo:
        return "facturacion"
    if "429" in texto or "resource_exhausted" in bajo or "quota" in bajo:
        return "rate_limit"
    if "api key" in bajo or "api_key" in bajo or "permission_denied" in bajo or "401" in texto or "403" in texto:
        return "auth"
    if "404" in texto and "model" in bajo:
        return "modelo_no_disponible"
    if "timeout" in bajo or "deadline" in bajo:
        return "timeout"
    if "500" in texto or "503" in texto or "unavailable" in bajo or "internal" in bajo:
        return "proveedor_5xx"
    if "400" in texto or "invalid_argument" in bajo or "contents" in bajo and "empty" in bajo:
        return "entrada_invalida"
    if "recursion" in bajo:
        return "limite_recursion"
    return "otro"


def sanitizar_error(exc: BaseException | str, largo: int = 180) -> str:
    texto = redactar_secretos(str(exc))
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:largo]


# --------------------------------------------------------------------------
# Logger JSONL
# --------------------------------------------------------------------------
class RegistroEventos:
    """Escribe un evento por línea (JSON) en logs.jsonl. Seguro entre hilos."""

    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def escribir(self, evento: dict):
        with self._lock, self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(sanitizar_datos(evento), ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# Callback por etapas
# --------------------------------------------------------------------------
class TrazadorEtapas(BaseCallbackHandler):
    """Mide las etapas de una solicitud. Crear uno nuevo por solicitud."""

    raise_error = False  # un fallo del trazador nunca debe romper al agente

    def __init__(self, request_id: str, contexto: dict, registro: RegistroEventos):
        self.request_id = request_id
        self.contexto = contexto  # scenario, caso_id, repeticion, version
        self.registro = registro
        self._inicio: dict[UUID, tuple[float, str, str]] = {}
        self._lock = threading.Lock()
        self.n_llm = 0
        self.n_tools = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.ms_llm = 0.0
        self.ms_tools = 0.0
        self.errores_tool = 0

    # -- utilidades
    def _abrir(self, run_id: UUID, stage: str, ts: str):
        with self._lock:
            self._inicio[run_id] = (time.perf_counter(), stage, ts)

    def _cerrar(self, run_id: UUID, status: str, error_type: str = "", error: str = "", extra=None):
        with self._lock:
            ini = self._inicio.pop(run_id, None)
        if ini is None:
            return 0.0, ""
        t0, stage, ts = ini
        dur = (time.perf_counter() - t0) * 1000
        evento = {
            "request_id": self.request_id,
            "timestamp": ts,
            "stage": stage,
            "duration_ms": round(dur, 1),
            "status": status,
            "error_type": error_type,
            "error": error,
            **self.contexto,
            **(extra or {}),
        }
        self.registro.escribir(evento)
        return dur, stage

    # -- LLM
    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs: Any):
        self._abrir(run_id, "llm", ahora_iso())

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs: Any):
        self._abrir(run_id, "llm", ahora_iso())

    def on_llm_end(self, response, *, run_id, **kwargs: Any):
        tin = tout = 0
        try:
            msg = response.generations[0][0].message
            uso = getattr(msg, "usage_metadata", None) or {}
            tin, tout = int(uso.get("input_tokens", 0)), int(uso.get("output_tokens", 0))
        except Exception:
            pass
        dur, _ = self._cerrar(run_id, "ok", extra={"tokens_in": tin, "tokens_out": tout})
        with self._lock:
            self.n_llm += 1
            self.tokens_in += tin
            self.tokens_out += tout
            self.ms_llm += dur

    def on_llm_error(self, error, *, run_id, **kwargs: Any):
        dur, _ = self._cerrar(run_id, "error", clasificar_error(error), sanitizar_error(error))
        with self._lock:
            self.n_llm += 1
            self.ms_llm += dur

    # -- Herramientas
    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs: Any):
        nombre = (serialized or {}).get("name") or kwargs.get("name") or "desconocida"
        self._abrir(run_id, f"tool:{nombre}", ahora_iso())

    def on_tool_end(self, output, *, run_id, **kwargs: Any):
        texto = str(getattr(output, "content", output))
        # Las herramientas devuelven texto; "No hay datos" es un resultado válido pero vacío.
        vacio = "no hay datos" in texto.lower() or "no se encontraron" in texto.lower()
        invalida = texto.lower().startswith("consulta inválida")
        dur, _ = self._cerrar(run_id, "entrada_invalida" if invalida else ("sin_datos" if vacio else "ok"))
        with self._lock:
            self.n_tools += 1
            self.ms_tools += dur

    def on_tool_error(self, error, *, run_id, **kwargs: Any):
        dur, _ = self._cerrar(run_id, "error", "tool_error", sanitizar_error(error))
        with self._lock:
            self.n_tools += 1
            self.errores_tool += 1
            self.ms_tools += dur


# --------------------------------------------------------------------------
# Recursos
# --------------------------------------------------------------------------
class MuestreadorRecursos:
    """Muestrea CPU % (100 % = un núcleo completo) y RSS en MB del proceso."""

    def __init__(self, intervalo: float = 0.1):
        self.intervalo = intervalo
        self._cpu: list[float] = []
        self._ram: list[float] = []
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)

    def _bucle(self):
        PROCESO.cpu_percent(None)  # primera lectura de referencia
        while not self._parar.wait(self.intervalo):
            self._cpu.append(PROCESO.cpu_percent(None))
            self._ram.append(PROCESO.memory_info().rss / 2**20)

    def __enter__(self):
        self._cpu_t0 = PROCESO.cpu_times()
        self._t0 = time.perf_counter()
        self._hilo.start()
        return self

    def __exit__(self, *exc):
        self._parar.set()
        self._hilo.join()
        t1 = PROCESO.cpu_times()
        pared = time.perf_counter() - self._t0
        cpu_seg = (t1.user - self._cpu_t0.user) + (t1.system - self._cpu_t0.system)
        ram_final = PROCESO.memory_info().rss / 2**20
        self.resultado = {
            # CPU promedio de la solicitud = tiempo de CPU del proceso / tiempo de pared
            "cpu_pct": round(100 * cpu_seg / pared, 1) if pared > 0 else 0.0,
            "cpu_pct_max": round(max(self._cpu, default=0.0), 1),
            "ram_mb": round(ram_final, 1),
            "ram_peak_mb": round(max(self._ram + [ram_final]), 1),
            "cpu_seg": round(cpu_seg, 3),
        }
        return False
