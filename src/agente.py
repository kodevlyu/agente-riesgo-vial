import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.consulta import consultar_siniestros

load_dotenv()

SISTEMA = (
    "Eres un asistente experto en seguridad vial en Chile. "
    "Respondes en español, de forma clara y breve. "
    "Para cualquier dato sobre siniestros (cantidades, causas, rutas, clima, víctimas) "
    "DEBES usar la herramienta consultar_siniestros y basarte solo en lo que devuelva. "
    "Si la herramienta no entrega datos suficientes, dilo explícitamente. "
    "Los datos son simulados con fines académicos."
)

TOOLS = [consultar_siniestros]


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
        "¿Cuáles son las principales causas de siniestros en Melipilla "
        "y qué ruta es la más afectada?"
    )
    resultado = agente.invoke({"messages": [HumanMessage(content=pregunta)]}, config)

    for m in resultado["messages"]:
        if m.type == "ai" and m.tool_calls:
            for tc in m.tool_calls:
                print(f"[TOOL] {tc['name']} <- {tc['args']}")
    print("\n[RESPUESTA]")
    print(resultado["messages"][-1].text)