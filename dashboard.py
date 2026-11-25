
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="Risk AI | Observabilidad",
    page_icon="📊",
    layout="wide"
)

ROOT = Path(__file__).resolve().parent
RESULTADOS = ROOT / "resultados"
BASE = RESULTADOS / "base"
ANALISIS = BASE / "analisis"

MORADO = "#A78BFA"
VERDE = "#34D399"
ROJO = "#F87171"
AZUL = "#60A5FA"
GRIS = "#64748B"

ESCENARIOS = {
    "normal": "Normal",
    "complejo": "Complejo",
    "incompleto": "Incompleto",
    "erroneo": "Erróneo",
    "sistema": "Sistema"
}

# ==================================================
# ESTILOS
# ==================================================

st.markdown("""
<style>
[data-testid="stMetric"] {
    background-color: #211C30;
    border: 1px solid #49336B;
    padding: 20px;
    border-radius: 14px;
}
[data-testid="stMetricValue"] {
    color: #C4A5FF;
}
[data-testid="stMetricLabel"] {
    color: #E4D9FF;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# CARGA DE DATOS
# ==================================================

@st.cache_data
def cargar_datos():
    with open(
        ANALISIS / "metricas.json",
        encoding="utf-8"
    ) as archivo:
        metricas = json.load(archivo)

    resultados = pd.read_csv(
        BASE / "resultados.csv",
        encoding="utf-8"
    )

    casos = pd.read_csv(ANALISIS / "por_caso.csv")
    escenarios = pd.read_csv(ANALISIS / "por_escenario.csv")
    etapas = pd.read_csv(ANALISIS / "etapas.csv")
    anomalias = pd.read_csv(ANALISIS / "anomalias.csv")
    errores = pd.read_csv(ANALISIS / "errores.csv")

    logs = pd.read_json(
        BASE / "logs.jsonl",
        lines=True,
        encoding="utf-8"
    )

    return (
        metricas, resultados, casos, escenarios,
        etapas, anomalias, errores, logs
    )


try:
    (
        metricas, resultados, casos, escenarios,
        etapas, anomalias, errores, logs
    ) = cargar_datos()

except (OSError, ValueError) as error:
    st.error(f"Error al cargar los datos: {error}")
    st.stop()

# ==================================================
# MENÚ Y FILTROS
# ==================================================

with st.sidebar:

    st.title("📊 RISK AI")
    st.caption("Sistema de observabilidad")

    pagina = st.radio(
        "Navegación",
        [
            "Resumen general",
            "Rendimiento",
            "Precisión y consistencia",
            "Logs y anomalías",
            "Comparación"
        ]
    )

    st.divider()
    st.subheader("Filtros")

    opciones_escenario = sorted(
        resultados["scenario"].dropna().unique()
    )

    filtro_escenario = st.multiselect(
        "Escenarios",
        options=opciones_escenario,
        default=opciones_escenario,
        format_func=lambda x: ESCENARIOS.get(x, x)
    )

    datos_escenario = resultados[
        resultados["scenario"].isin(filtro_escenario)
    ]

    opciones_caso = sorted(
        datos_escenario["caso_id"].unique()
    )

    filtro_caso = st.multiselect(
        "Casos",
        options=opciones_caso,
        default=opciones_caso,
        key="casos_" + "_".join(filtro_escenario)
    )

    opciones_estado = sorted(
        resultados["status"].dropna().unique()
    )

    filtro_estado = st.multiselect(
        "Estado de ejecución",
        options=opciones_estado,
        default=opciones_estado
    )

    st.divider()

    st.caption("Ingeniería de Soluciones con IA")
    st.caption("Evaluación Parcial 3")
    st.caption("Duoc UC | 2026")

    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

# ==================================================
# APLICAR FILTROS
# ==================================================

datos = resultados[
    resultados["scenario"].isin(filtro_escenario)
    & resultados["caso_id"].isin(filtro_caso)
    & resultados["status"].isin(filtro_estado)
].copy()

ids = datos["request_id"].unique()

anomalias_filtradas = anomalias[
    anomalias["request_id"].isin(ids)
].copy()

logs_filtrados = logs[
    logs["request_id"].isin(ids)
].copy()

# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

def mostrar_grafico(fig):
    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=30),
        legend_title_text=""
    )
    st.plotly_chart(fig, use_container_width=True)


def calcular_consistencia(df):
    coincidencias = 0
    total = 0

    for _, grupo in df.groupby("caso_id"):
        firmas = grupo["firma"].dropna()

        if not firmas.empty:
            coincidencias += firmas.value_counts().max()
            total += len(firmas)

    return coincidencias / total * 100 if total else 0


def resumen_filtrado(df):
    return {
        "precision_pct": df["correct"].mean() * 100,
        "consistencia_pct": calcular_consistencia(df),
        "tasa_error_pct": (
            df["status"].ne("ok").mean() * 100
        ),
        "latencia_media_ms": df["latency_ms"].mean(),
        "cpu_pct_media": df["cpu_pct"].mean(),
        "ram_mb_media": df["ram_mb"].mean(),
        "latencia_p95_ms": df["latency_ms"].quantile(0.95),
        "ejecuciones": len(df),
        "casos": df["caso_id"].nunique()
    }


st.title("Observabilidad del agente de riesgo vial")

st.caption(
    "Evaluación de precisión, rendimiento y confiabilidad"
)

modelos = ", ".join(
    resultados["modelo"].dropna().unique()
)

st.info(
    f"Fuente: línea base original | Modelo: {modelos}"
)

if datos.empty and pagina != "Comparación":
    st.warning("No existen ejecuciones para los filtros seleccionados.")
    st.stop()

if not datos.empty:
    indicadores = (
        metricas
        if len(datos) == len(resultados)
        else resumen_filtrado(datos)
    )

    st.caption(
        f"Ejecuciones seleccionadas: "
        f"{len(datos)} de {len(resultados)}"
    )

# ==================================================
# RESUMEN GENERAL
# ==================================================

if pagina == "Resumen general":

    st.header("Resumen general")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Precisión",
        f"{indicadores['precision_pct']:.1f}%"
    )

    c2.metric(
        "Consistencia",
        f"{indicadores['consistencia_pct']:.1f}%"
    )

    c3.metric(
        "Errores técnicos",
        f"{indicadores['tasa_error_pct']:.1f}%"
    )

    c4, c5, c6 = st.columns(3)

    c4.metric(
        "Latencia promedio",
        f"{indicadores['latencia_media_ms'] / 1000:.2f} s"
    )

    c5.metric(
        "CPU promedio",
        f"{indicadores['cpu_pct_media']:.1f}%"
    )

    c6.metric(
        "RAM promedio",
        f"{indicadores['ram_mb_media']:.1f} MB"
    )

    st.divider()

    a, b, c = st.columns(3)

    a.metric("Ejecuciones", indicadores["ejecuciones"])
    b.metric("Casos evaluados", indicadores["casos"])

    c.metric(
        "Latencia P95",
        f"{indicadores['latencia_p95_ms'] / 1000:.2f} s"
    )

    st.subheader("Distribución del tiempo de procesamiento")

    total = datos["latency_ms"].sum()
    llm = datos["llm_ms"].sum()
    tools = datos["tools_ms"].sum()
    otros = max(0, total - llm - tools)

    distribucion = pd.DataFrame({
        "Componente": ["LLM", "Herramientas", "Otros"],
        "Tiempo": [llm, tools, otros]
    })

    fig = px.pie(
        distribucion,
        names="Componente",
        values="Tiempo",
        hole=0.65,
        color_discrete_sequence=[MORADO, VERDE, GRIS]
    )

    fig.update_traces(textinfo="percent+label")

    mostrar_grafico(fig)

    st.subheader("Hallazgos globales de la línea base")

    st.warning("N4: precisión de 33.3% en tres ejecuciones.")
    st.warning("El LLM concentra el 93.1% del tiempo total.")
    st.success("Sin errores técnicos en las 39 pruebas originales.")

# ==================================================
# RENDIMIENTO
# ==================================================

elif pagina == "Rendimiento":

    st.header("Análisis de rendimiento")

    datos = datos.sort_values("timestamp")

    fig = px.line(
        datos,
        x="timestamp",
        y="latency_ms",
        markers=True,
        color="scenario",
        hover_data=["caso_id", "repeticion", "request_id"],
        title="Latencia por ejecución",
        labels={
            "timestamp": "Fecha y hora",
            "latency_ms": "Latencia (ms)",
            "scenario": "Escenario"
        },
        color_discrete_sequence=[
            MORADO, VERDE, AZUL, ROJO
        ]
    )

    fig.add_hline(
        y=metricas["latencia_p95_ms"],
        line_dash="dash",
        line_color=ROJO,
        annotation_text="P95 global"
    )

    mostrar_grafico(fig)

    rendimiento = datos.groupby(
        "caso_id", as_index=False
    ).agg(
        latencia=("latency_ms", "mean"),
        cpu=("cpu_pct", "mean"),
        ram=("ram_peak_mb", "max")
    )

    fig = px.bar(
        rendimiento,
        x="caso_id",
        y="latencia",
        title="Latencia promedio por caso",
        labels={
            "caso_id": "Caso",
            "latencia": "Latencia (ms)"
        },
        color_discrete_sequence=[MORADO]
    )

    mostrar_grafico(fig)

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            rendimiento,
            x="caso_id",
            y="cpu",
            title="CPU promedio",
            labels={
                "caso_id": "Caso",
                "cpu": "CPU (%)"
            },
            color_discrete_sequence=[MORADO]
        )
        mostrar_grafico(fig)

    with c2:
        fig = px.bar(
            rendimiento,
            x="caso_id",
            y="ram",
            title="Pico de memoria RAM",
            labels={
                "caso_id": "Caso",
                "ram": "Memoria (MB)"
            },
            color_discrete_sequence=[VERDE]
        )
        mostrar_grafico(fig)

    st.subheader("Cuellos de botella")

    etapas_filtradas = logs_filtrados.groupby(
        "stage", as_index=False
    ).agg(
        llamadas=("duration_ms", "count"),
        promedio_ms=("duration_ms", "mean"),
        total_ms=("duration_ms", "sum")
    )

    total_etapas = etapas_filtradas["total_ms"].sum()

    etapas_filtradas["porcentaje"] = (
        etapas_filtradas["total_ms"] / total_etapas * 100
        if total_etapas > 0 else 0
    )

    fig = px.bar(
        etapas_filtradas.sort_values("total_ms"),
        x="total_ms",
        y="stage",
        orientation="h",
        title="Tiempo acumulado por etapa",
        labels={
            "total_ms": "Tiempo acumulado (ms)",
            "stage": "Etapa"
        },
        color_discrete_sequence=[MORADO]
    )

    mostrar_grafico(fig)

    st.dataframe(
        etapas_filtradas.round(2).rename(columns={
            "stage": "Etapa",
            "llamadas": "Llamadas",
            "promedio_ms": "Promedio (ms)",
            "total_ms": "Total (ms)",
            "porcentaje": "% del tiempo registrado"
        }),
        hide_index=True,
        use_container_width=True
    )

# ==================================================
# PRECISIÓN Y CONSISTENCIA
# ==================================================

elif pagina == "Precisión y consistencia":

    st.header("Calidad de las respuestas")

    calidad = datos.groupby(
        "caso_id", as_index=False
    ).agg(
        precision=("correct", "mean"),
        ejecuciones=("request_id", "count")
    )

    calidad["Precisión (%)"] = calidad["precision"] * 100

    calidad["Consistencia (%)"] = calidad["caso_id"].map(
        lambda caso: calcular_consistencia(
            datos[datos["caso_id"] == caso]
        )
    )

    fig = px.bar(
        calidad,
        x="caso_id",
        y=["Precisión (%)", "Consistencia (%)"],
        barmode="group",
        title="Precisión y consistencia por caso",
        labels={
            "caso_id": "Caso",
            "value": "Porcentaje (%)",
            "variable": "Indicador"
        },
        color_discrete_sequence=[MORADO, VERDE]
    )

    fig.update_yaxes(range=[0, 105])
    mostrar_grafico(fig)

    por_escenario = datos.groupby(
        "scenario", as_index=False
    ).agg(
        precision=("correct", "mean"),
        ejecuciones=("request_id", "count"),
        latencia=("latency_ms", "mean")
    )

    por_escenario["Precisión (%)"] = (
        por_escenario["precision"] * 100
    )

    por_escenario["Escenario"] = (
        por_escenario["scenario"].map(ESCENARIOS)
    )

    fig = px.bar(
        por_escenario,
        x="Escenario",
        y="Precisión (%)",
        title="Precisión por escenario",
        color_discrete_sequence=[MORADO]
    )

    fig.update_yaxes(range=[0, 105])
    mostrar_grafico(fig)

    st.subheader("Resultados detallados")

    tabla = datos[[
        "caso_id", "scenario", "repeticion",
        "expected", "correct", "detalle", "latency_ms"
    ]].copy()

    tabla["correct"] = tabla["correct"].map({
        1: "Correcta",
        0: "Incorrecta"
    })

    tabla = tabla.rename(columns={
        "caso_id": "Caso",
        "scenario": "Escenario",
        "repeticion": "Repetición",
        "expected": "Resultado esperado",
        "correct": "Evaluación",
        "detalle": "Detalle",
        "latency_ms": "Latencia (ms)"
    })

    st.dataframe(
        tabla,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "Descargar resultados filtrados",
        datos.to_csv(index=False).encode("utf-8-sig"),
        file_name="resultados_filtrados.csv",
        mime="text/csv"
    )

# ==================================================
# LOGS Y ANOMALÍAS
# ==================================================

elif pagina == "Logs y anomalías":

    st.header("Detección de anomalías")

    c1, c2 = st.columns(2)

    c1.metric(
        "Registros de anomalías",
        len(anomalias_filtradas)
    )

    c2.metric(
        "Solicitudes afectadas",
        anomalias_filtradas["request_id"].nunique()
    )

    # Separar solicitudes completas de etapas internas.

    anomalias_ejecucion = anomalias_filtradas[
        anomalias_filtradas["n_llm"].notna()
    ].copy()

    anomalias_etapa = anomalias_filtradas[
        anomalias_filtradas["n_llm"].isna()
    ].copy()

    if not anomalias_ejecucion.empty:

        anomalias_ejecucion["Ejecución"] = (
            anomalias_ejecucion["caso_id"]
            + " - R"
            + anomalias_ejecucion["repeticion"].astype(str)
        )

        fig = px.bar(
            anomalias_ejecucion,
            x="Ejecución",
            y="latency_ms",
            color="herramientas",
            barmode="group",
            hover_data=["request_id", "motivos"],
            title="Latencia de ejecuciones anómalas",
            labels={
                "latency_ms": "Latencia (ms)",
                "herramientas": "Herramienta"
            },
            color_discrete_sequence=[MORADO, AZUL, ROJO]
        )

        mostrar_grafico(fig)

    st.subheader("Detalle de anomalías")

    st.dataframe(
        anomalias_filtradas.rename(columns={
            "request_id": "ID de solicitud",
            "caso_id": "Caso",
            "repeticion": "Repetición",
            "latency_ms": "Latencia (ms)",
            "n_llm": "Llamadas LLM",
            "herramientas": "Herramientas",
            "motivos": "Motivos"
        }),
        hide_index=True,
        use_container_width=True
    )

    if not anomalias_etapa.empty:
        st.subheader("Anomalías en etapas internas")

        st.dataframe(
            anomalias_etapa,
            hide_index=True,
            use_container_width=True
        )

    st.subheader("Errores técnicos — globales")

    st.dataframe(
        errores,
        hide_index=True,
        use_container_width=True
    )

    st.divider()
    st.subheader("Explorador de logs")

    incluir_sistema = st.checkbox(
        "Incluir registros de inicialización"
    )

    registros = logs_filtrados.copy()

    if incluir_sistema:
        registros = pd.concat([
            registros,
            logs[logs["scenario"] == "sistema"]
        ]).drop_duplicates()

    etapas_disponibles = sorted(
        registros["stage"].dropna().unique()
    )

    etapa_seleccionada = st.multiselect(
        "Filtrar por etapa",
        etapas_disponibles,
        default=etapas_disponibles
    )

    registros = registros[
        registros["stage"].isin(etapa_seleccionada)
    ]

    busqueda = st.text_input(
        "Buscar por ID, caso, etapa o contenido"
    )

    if busqueda:
        coincidencias = registros.astype(str).apply(
            lambda columna: columna.str.contains(
                busqueda,
                case=False,
                regex=False
            )
        ).any(axis=1)

        registros = registros[coincidencias]

    st.caption(f"Registros encontrados: {len(registros)}")

    st.dataframe(
        registros,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "Descargar logs filtrados",
        registros.to_csv(index=False).encode("utf-8-sig"),
        file_name="logs_filtrados.csv",
        mime="text/csv"
    )

# ==================================================
# COMPARACIÓN
# ==================================================

elif pagina == "Comparación":

    st.header("Comparación antes y después")

    st.caption("Comparación global, independiente de los filtros.")

    ruta_mejorada = (
        RESULTADOS / "mejorado" / "analisis" / "metricas.json"
    )

    if ruta_mejorada.exists():

        with open(ruta_mejorada, encoding="utf-8") as archivo:
            mejorado = json.load(archivo)

        indicadores_comparacion = {
            "Precisión (%)": "precision_pct",
            "Consistencia (%)": "consistencia_pct",
            "Errores (%)": "tasa_error_pct",
            "Latencia (ms)": "latencia_media_ms",
            "CPU (%)": "cpu_pct_media",
            "RAM (MB)": "ram_mb_media"
        }

        comparacion = pd.DataFrame([
            {
                "Indicador": nombre,
                "Antes": metricas[clave],
                "Después": mejorado[clave],
                "Diferencia": round(
                    mejorado[clave] - metricas[clave], 2
                )
            }
            for nombre, clave
            in indicadores_comparacion.items()
        ])

        st.dataframe(
            comparacion,
            hide_index=True,
            use_container_width=True
        )

        for _, fila in comparacion.iterrows():

            df = pd.DataFrame({
                "Versión": ["Antes", "Después"],
                "Valor": [fila["Antes"], fila["Después"]]
            })

            fig = px.bar(
                df,
                x="Versión",
                y="Valor",
                color="Versión",
                title=fila["Indicador"],
                color_discrete_sequence=[GRIS, MORADO]
            )

            mostrar_grafico(fig)

        st.download_button(
            "Descargar comparación",
            comparacion.to_csv(index=False).encode("utf-8-sig"),
            file_name="comparacion_metricas.csv",
            mime="text/csv"
        )

    else:

        st.warning(
            "Las pruebas posteriores a las mejoras "
            "todavía no se han ejecutado."
        )

        st.write(
            "La comparación se habilitará cuando existan "
            "resultados reales de la versión mejorada."
        )

st.divider()

st.caption(
    "Risk AI | Observabilidad de soluciones "
    "con inteligencia artificial"
)
