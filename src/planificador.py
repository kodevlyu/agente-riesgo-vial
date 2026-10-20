import os
import sys
import uuid
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.agente import construir_agente
from src.tools.riesgo import calcular_riesgo_comuna, ranking_riesgo

load_dotenv()
from src.errores import instalar_manejo_errores
instalar_manejo_errores()

MAX_REPLANES = 2
MARCAS_FALLO = ("No hay datos", "No se encontraron")


class Paso(BaseModel):
    descripcion: str = Field(
        description="Acción concreta y autocontenida (nombra comuna y clima si aplica)"
    )
    prioridad: int = Field(description="1 = alta, 2 = media, 3 = baja")


class Plan(BaseModel):
    pasos: list[Paso]


class Estado(TypedDict):
    pregunta: str
    pasos: list[dict]
    resultados: list[str]
    fallo: str
    replanes: int
    respuesta: str


HERRAMIENTAS_TXT = (
    "consultar_siniestros (busca siniestros y resúmenes por comuna), "
    "calcular_riesgo_comuna (puntaje de una comuna, con clima opcional), "
    "ranking_riesgo (comunas más riesgosas, con clima opcional), "
    "guardar_reporte (guarda un reporte Markdown en outputs/), "
    "buscar_recuerdos y guardar_recuerdo (memoria de largo plazo)"
)


def _llm():
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        temperature=0,
    )


def _ordenar(pasos: list[Paso]) -> list[dict]:
    # sorted es estable: a igual prioridad se mantiene el orden original
    return sorted((p.model_dump() for p in pasos), key=lambda p: p["prioridad"])


def construir_planificador():
    agente = construir_agente()
    llm = _llm()
    planner = llm.with_structured_output(Plan)

    def nodo_planificar(state: Estado):
        prompt = (
            "Eres el planificador de un agente de seguridad vial en Chile. "
            "Descompón la petición en 2 a 5 pasos concretos, ejecutables con estas "
            f"herramientas: {HERRAMIENTAS_TXT}. "
            "Asigna prioridad 1 (crítico), 2 o 3. La prioridad también ordena la "
            "ejecución: los números menores se ejecutan antes. "
            "Si la petición menciona 'mi comuna' o una preferencia personal, el primer "
            "paso (prioridad 1) debe ser buscar_recuerdos. "
            "Si piden un reporte, el último paso debe guardarlo con guardar_reporte y "
            "tener prioridad 3, porque necesita los datos de los pasos anteriores.\n\n"
            f"Petición: {state['pregunta']}"
        )
        plan = planner.invoke(prompt)
        pasos = _ordenar(plan.pasos)
        print("\n[PLAN]")
        for i, p in enumerate(pasos, 1):
            print(f"  {i}. (prioridad {p['prioridad']}) {p['descripcion']}")
        return {"pasos": pasos}

    def nodo_ejecutar(state: Estado):
        paso, resto = state["pasos"][0], state["pasos"][1:]
        n = len(state["resultados"]) + 1
        print(f"\n[PASO {n}] {paso['descripcion']}")
        contexto = "\n".join(f"- {r}" for r in state["resultados"]) or "(ninguno todavía)"
        instruccion = (
            f"Petición original del usuario: {state['pregunta']}\n"
            f"Resultados de pasos anteriores:\n{contexto}\n\n"
            f"Ejecuta SOLO este paso: {paso['descripcion']}"
        )
        config = {"configurable": {"thread_id": f"paso-{uuid.uuid4().hex[:8]}"}}
        res = agente.invoke({"messages": [HumanMessage(content=instruccion)]}, config)

        fallo = ""
        for m in res["messages"]:
            if m.type == "ai" and m.tool_calls:
                for tc in m.tool_calls:
                    print(f"   [TOOL] {tc['name']} <- {tc['args']}")
            if m.type == "tool" and any(x in str(m.content) for x in MARCAS_FALLO):
                fallo = str(m.content)
        texto = res["messages"][-1].text

        if fallo:
            print(f"   [FALLO] {fallo}")
            resultado = f"Paso: {paso['descripcion']} -> FALLÓ: {fallo}"
        else:
            print("   [OK]")
            resultado = f"Paso: {paso['descripcion']} -> {texto}"
        return {
            "pasos": resto,
            "resultados": state["resultados"] + [resultado],
            "fallo": fallo,
        }

    def nodo_replanificar(state: Estado):
        n = state["replanes"] + 1
        print(f"\n[REPLANIFICACIÓN {n}/{MAX_REPLANES}]")
        pendientes = "\n".join(f"- {p['descripcion']}" for p in state["pasos"]) or "(ninguno)"
        resultados = "\n".join(f"- {r}" for r in state["resultados"])
        prompt = (
            "Un paso del plan de un agente de seguridad vial falló por datos faltantes. "
            f"Herramientas disponibles: {HERRAMIENTAS_TXT}.\n\n"
            f"Petición original: {state['pregunta']}\n"
            f"Resultados hasta ahora:\n{resultados}\n"
            f"Pasos que estaban pendientes:\n{pendientes}\n\n"
            "Genera un nuevo plan SOLO con los pasos que aún faltan, adaptado al fallo: "
            "por ejemplo verificar nombres válidos con ranking_riesgo, probar otra "
            "comuna cercana o continuar sin ese dato si no es esencial. "
            "No repitas el paso fallido tal cual. Si hay un reporte pendiente, déjalo "
            "al final con prioridad 3 y que mencione la limitación encontrada. "
            "Si ya no falta nada, devuelve una lista vacía."
        )
        plan = planner.invoke(prompt)
        pasos = _ordenar(plan.pasos)
        for i, p in enumerate(pasos, 1):
            print(f"  {i}. (prioridad {p['prioridad']}) {p['descripcion']}")
        return {"pasos": pasos, "replanes": n, "fallo": ""}

    def nodo_sintetizar(state: Estado):
        resultados = "\n".join(f"- {r}" for r in state["resultados"])
        prompt = (
            "Responde al usuario en español, de forma clara y breve, usando SOLO "
            "los resultados de los pasos ejecutados. Si algún paso falló o hubo que "
            "replanificar, explícalo con honestidad. Los datos son simulados.\n\n"
            f"Petición: {state['pregunta']}\n"
            f"Resultados:\n{resultados}"
        )
        return {"respuesta": llm.invoke(prompt).text}

    def tras_planificar(state: Estado):
        return "ejecutar" if state["pasos"] else "sintetizar"

    def tras_ejecutar(state: Estado):
        if state["fallo"] and state["replanes"] < MAX_REPLANES:
            return "replanificar"
        return "ejecutar" if state["pasos"] else "sintetizar"

    def tras_replanificar(state: Estado):
        return "ejecutar" if state["pasos"] else "sintetizar"

    g = StateGraph(Estado)
    g.add_node("planificar", nodo_planificar)
    g.add_node("ejecutar", nodo_ejecutar)
    g.add_node("replanificar", nodo_replanificar)
    g.add_node("sintetizar", nodo_sintetizar)
    g.add_edge(START, "planificar")
    g.add_conditional_edges("planificar", tras_planificar, ["ejecutar", "sintetizar"])
    g.add_conditional_edges(
        "ejecutar", tras_ejecutar, ["ejecutar", "replanificar", "sintetizar"]
    )
    g.add_conditional_edges("replanificar", tras_replanificar, ["ejecutar", "sintetizar"])
    g.add_edge("sintetizar", END)
    return g.compile()


if __name__ == "__main__":
    # Uso: python -m src.planificador "petición"
    pregunta = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Hazme un reporte de riesgo de la comuna de Pirque cuando llueve."
    )
    app = construir_planificador()
    print(f"[PETICIÓN] {pregunta}")
    final = app.invoke(
        {
            "pregunta": pregunta,
            "pasos": [],
            "resultados": [],
            "fallo": "",
            "replanes": 0,
            "respuesta": "",
        },
        {"recursion_limit": 40},
    )
    print("\n[RESPUESTA FINAL]")
    print(final["respuesta"])
    print(f"\n[RESUMEN] pasos ejecutados: {len(final['resultados'])}, replanificaciones: {final['replanes']}")