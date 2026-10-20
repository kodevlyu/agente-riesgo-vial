import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.consulta import consultar_siniestros
from src.tools.reporte import guardar_reporte
from src.tools.riesgo import calcular_riesgo_comuna, ranking_riesgo

load_dotenv()

SISTEMA = (
    "Eres un asistente experto en seguridad vial en Chile. "
    "Respondes en español, de forma clara y breve. "
    "Tienes cuatro herramientas: "
    "consultar_siniestros (busca siniestros concretos y resúmenes por comuna), "
    "calcular_riesgo_comuna (puntaje de riesgo de una comuna, con clima opcional), "
    "ranking_riesgo (comunas más riesgosas, con clima opcional) y "
    "guardar_reporte (guarda un reporte en Markdown en outputs/). "
    "Para cualquier dato debes usar las herramientas y basarte solo en lo que devuelvan. "
    "Si piden comparar condiciones (por ejemplo con y sin lluvia), llama la herramienta "
    "una vez por cada condición. "
    "Si piden un reporte, primero reúne los datos con las otras herramientas y al final "
    "llama guardar_reporte con el contenido completo en Markdown. "
    "Si las herramientas no entregan datos suficientes, dilo explícitamente. "
    "Los datos son simulados con fines académicos."
)

TOOLS = [consultar_siniestros, calcular_riesgo_comuna, ranking_riesgo, guardar_reporte]


def construir_agente():
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        temperature=0,
    )
    llm_con_tools = llm.bind_tools(TOOLS)

    def nodo_agente(state: MessagesState):
        mensajes = [SystemMessage(content=SISTEMA)] + state["messages"]
        return {"messages": [llm_con_tools.invoke(mensajes)]}

    grafo = StateGraph(MessagesState)
    grafo.add_node("agente", nodo_agente)
    grafo.add_node("tools", ToolNode(TOOLS))
    grafo.add_edge(START, "agente")
    grafo.add_conditional_edges("agente", tools_condition)
    grafo.add_edge("tools", "agente")
    return grafo.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    agente = construir_agente()
    config = {"configurable": {"thread_id": "prueba-1"}}
    pregunta = (
        "Genera un reporte con las 3 comunas más riesgosas cuando llueve, "
        "e incluye la causa más frecuente de siniestros de la primera."
    )
    resultado = agente.invoke({"messages": [HumanMessage(content=pregunta)]}, config)

    for m in resultado["messages"]:
        if m.type == "ai" and m.tool_calls:
            for tc in m.tool_calls:
                print(f"[TOOL] {tc['name']} <- {tc['args']}")
    print("\n[RESPUESTA]")
    print(resultado["messages"][-1].text)