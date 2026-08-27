from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st


# =========================================================
# CONFIGURACIÓN / RUTAS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOCALIDADES_CSV = DATA_DIR / "localidades.csv"

TOTAL_LOCALIDADES_PDL = 149
LOCALIDAD_INICIAL = "Tejupilco de Hidalgo"


# =========================================================
# CARGA DE DATOS
# =========================================================

@st.cache_data
def cargar_localidades() -> pd.DataFrame:
    """
    Carga el catálogo base de localidades desde CSV.

    Columnas requeridas:
    id_pdl,nombre,lat,lon,poblacion,estado
    """

    if not LOCALIDADES_CSV.exists():
        st.error(
            f"No se encontró el archivo de localidades:\n\n"
            f"`{LOCALIDADES_CSV}`"
        )
        st.stop()

    df = pd.read_csv(LOCALIDADES_CSV)

    columnas_requeridas = {
        "id_pdl",
        "nombre",
        "lat",
        "lon",
        "poblacion",
        "estado",
    }

    faltantes = columnas_requeridas - set(df.columns)

    if faltantes:
        st.error(
            "El archivo `localidades.csv` no contiene todas las "
            f"columnas requeridas.\n\nFaltan: {', '.join(sorted(faltantes))}"
        )
        st.stop()

    # Normalización básica
    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["estado"] = df["estado"].astype(str).str.strip().str.lower()

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["poblacion"] = pd.to_numeric(df["poblacion"], errors="coerce")

    return df


# =========================================================
# UTILIDADES
# =========================================================

def obtener_localidad_activa(df: pd.DataFrame) -> pd.Series | None:
    """Obtiene el registro correspondiente a la localidad activa."""

    nombre = st.session_state.get(
        "localidad_activa",
        LOCALIDAD_INICIAL,
    )

    coincidencia = df[df["nombre"] == nombre]

    if coincidencia.empty:
        return None

    return coincidencia.iloc[0]


def formato_poblacion(valor) -> str:
    """Formatea población sin romperse si el dato está vacío."""

    if pd.isna(valor):
        return "Pendiente"

    return f"{int(valor):,}"


# =========================================================
# SIDEBAR
# =========================================================

def render_sidebar() -> str:
    """Renderiza la navegación principal del PDL."""

    with st.sidebar:
        st.title("PDL")
        st.caption("Dashboard Vivo del Municipio")

        st.markdown("### Tejupilco")

        modulo = st.radio(
            "Navegación",
            [
                "Inicio",
                "Territorio",
                "Localidades",
                "Diagnóstico",
                "Planeación",
                "PbR / MIR",
                "Gestión Viva",
                "Datos",
            ],
        )

        st.divider()

        localidad = st.session_state.get(
            "localidad_activa",
            LOCALIDAD_INICIAL,
        )

        st.caption("Localidad activa")
        st.markdown(f"**{localidad}**")

        st.divider()

        st.caption(
            "Planeación de Desarrollo a nivel Localidad"
        )

    return modulo


# =========================================================
# HEADER / KPI
# =========================================================

def render_header() -> None:
    """Renderiza encabezado y métricas generales."""

    localidades = cargar_localidades()

    registros_cargados = len(localidades)

    con_datos = len(
        localidades[
            localidades["estado"].isin(
                ["parcial", "validado", "completo"]
            )
        ]
    )

    pendientes = max(
        TOTAL_LOCALIDADES_PDL - con_datos,
        0,
    )

    avance = (
        (con_datos / TOTAL_LOCALIDADES_PDL) * 100
        if TOTAL_LOCALIDADES_PDL
        else 0
    )

    st.title("PDL · Inteligencia Territorial Municipal")
    st.caption("Tejupilco · Estado de México")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Localidades",
        TOTAL_LOCALIDADES_PDL,
    )

    c2.metric(
        "Con datos",
        con_datos,
    )

    c3.metric(
        "Pendientes",
        pendientes,
    )

    c4.metric(
        "Avance",
        f"{avance:.1f} %",
    )

    st.caption(
        f"Registros actualmente cargados en catálogo: "
        f"{registros_cargados}"
    )

    st.divider()


# =========================================================
# INICIO
# =========================================================

def render_inicio() -> None:
    st.header("Dashboard Vivo del Municipio")

    st.write(
        """
        El PDL integra territorio, indicadores, diagnóstico por localidad,
        planeación, PbR-SEGEMUN, MIR, proyectos, gestión,
        evaluación y evidencia.
        """
    )

    st.info(
        "Flujo rector: Diagnóstico → Planeación → Presupuesto → "
        "Ejecución → Verificación → Resultado."
    )

    st.subheader("Arquitectura del PDL")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown("### 🔎")
    c1.markdown("**Diagnóstico**")

    c2.markdown("### 📖")
    c2.markdown("**Planeación**")

    c3.markdown("### 💰")
    c3.markdown("**PbR / MIR**")

    c4.markdown("### ⚙️")
    c4.markdown("**Gestión**")

    c5.markdown("### 📸")
    c5.markdown("**Evidencia**")


# =========================================================
# TERRITORIO
# =========================================================

def render_territorio() -> None:
    st.header("🗺️ Territorio")

    localidades = cargar_localidades()

    # Sólo registros que tienen coordenadas válidas
    geo = localidades.dropna(
        subset=["lat", "lon"]
    ).copy()

    if geo.empty:
        st.warning(
            "Todavía no existen localidades con coordenadas válidas."
        )
        return

    col_mapa, col_capas = st.columns(
        [4, 1],
        gap="large",
    )

    # -----------------------------------------------------
    # CAPAS
    # -----------------------------------------------------

    with col_capas:
        st.subheader("Capas")

        localidades_on = st.checkbox(
            "Localidades",
            value=True,
        )

        secciones_on = st.checkbox(
            "Secciones electorales",
            value=False,
            disabled=True,
        )

        carreteras_on = st.checkbox(
            "Carreteras",
            value=False,
            disabled=True,
        )

        escuelas_on = st.checkbox(
            "Escuelas",
            value=False,
            disabled=True,
        )

        salud_on = st.checkbox(
            "Salud",
            value=False,
            disabled=True,
        )

        denue_on = st.checkbox(
            "DENUE",
            value=False,
            disabled=True,
        )

        obras_on = st.checkbox(
            "Obras",
            value=False,
            disabled=True,
        )

        st.caption(
            "Las capas deshabilitadas se activarán cuando "
            "incorporemos sus GeoJSON."
        )

    # -----------------------------------------------------
    # LAYERS PYDECK
    # -----------------------------------------------------

    layers = []

    if localidades_on:
        capa_localidades = pdk.Layer(
            "ScatterplotLayer",
            data=geo,
            get_position="[lon, lat]",
            get_radius=450,
            radius_min_pixels=5,
            radius_max_pixels=18,
            get_fill_color="[0, 190, 190, 180]",
            get_line_color="[255, 255, 255, 180]",
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )

        layers.append(capa_localidades)

    # -----------------------------------------------------
    # VISTA
    # -----------------------------------------------------

    view = pdk.ViewState(
        latitude=18.90,
        longitude=-100.18,
        zoom=9.2,
        pitch=0,
        bearing=0,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip={
            "html": """
                <b>{nombre}</b><br/>
                ID PDL: {id_pdl}<br/>
                Población: {poblacion}<br/>
                Estado: {estado}
            """,
            "style": {
                "backgroundColor": "#0f172a",
                "color": "white",
                "fontSize": "13px",
            },
        },
    )

    with col_mapa:
        st.pydeck_chart(
            deck,
            use_container_width=True,
        )

    st.caption(
        "MVP cartográfico. Posteriormente los puntos serán "
        "complementados con geometrías oficiales GeoJSON/PostGIS."
    )

    # -----------------------------------------------------
    # TABLA TERRITORIAL
    # -----------------------------------------------------

    with st.expander("Ver localidades visibles en el mapa"):
        st.dataframe(
            geo[
                [
                    "id_pdl",
                    "nombre",
                    "lat",
                    "lon",
                    "poblacion",
                    "estado",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# LOCALIDADES
# =========================================================

def render_localidades() -> None:
    st.header("📍 Localidades")

    st.write(
        "Catálogo maestro, fichas territoriales y comparación "
        "entre localidades."
    )

    localidades = cargar_localidades()

    if localidades.empty:
        st.warning(
            "No existen localidades cargadas en el catálogo."
        )
        return

    nombres = localidades["nombre"].tolist()

    localidad_actual = st.session_state.get(
        "localidad_activa",
        LOCALIDAD_INICIAL,
    )

    if localidad_actual in nombres:
        indice_actual = nombres.index(localidad_actual)
    else:
        indice_actual = 0

    localidad = st.selectbox(
        "Localidad activa",
        nombres,
        index=indice_actual,
    )

    st.session_state["localidad_activa"] = localidad

    registro = localidades[
        localidades["nombre"] == localidad
    ].iloc[0]

    st.success(
        f"Localidad seleccionada: {localidad}"
    )

    # -----------------------------------------------------
    # KPI DE LOCALIDAD
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Población",
        formato_poblacion(
            registro["poblacion"]
        ),
    )

    c2.metric(
        "ID PDL",
        registro["id_pdl"],
    )

    c3.metric(
        "Estado",
        str(registro["estado"]).capitalize(),
    )

    coordenadas_validas = (
        pd.notna(registro["lat"])
        and pd.notna(registro["lon"])
    )

    c4.metric(
        "Georreferenciada",
        "Sí" if coordenadas_validas else "Pendiente",
    )

    st.divider()

    # -----------------------------------------------------
    # FICHA BÁSICA
    # -----------------------------------------------------

    st.subheader("Ficha territorial")

    izquierda, derecha = st.columns(2)

    with izquierda:
        st.markdown(
            f"""
            **Nombre:** {registro["nombre"]}

            **ID PDL:** {registro["id_pdl"]}

            **Estado del registro:** {registro["estado"]}
            """
        )

    with derecha:
        if coordenadas_validas:
            st.markdown(
                f"""
                **Latitud:** {registro["lat"]}

                **Longitud:** {registro["lon"]}

                **Población:** {formato_poblacion(registro["poblacion"])}
                """
            )
        else:
            st.warning(
                "Coordenadas pendientes de validar."
            )


# =========================================================
# DIAGNÓSTICO
# =========================================================

def render_diagnostico() -> None:
    st.header("📊 Diagnóstico")

    localidades = cargar_localidades()
    registro = obtener_localidad_activa(localidades)

    if registro is None:
        st.warning(
            "La localidad activa no existe en el catálogo."
        )
        return

    st.subheader(registro["nombre"])

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Población",
        formato_poblacion(
            registro["poblacion"]
        ),
    )

    c2.metric(
        "Estado de ficha",
        str(registro["estado"]).capitalize(),
    )

    c3.metric(
        "ID PDL",
        registro["id_pdl"],
    )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Indicadores",
            "Brechas",
            "FODA",
            "Árbol de problemas",
        ]
    )

    with tab1:
        st.info(
            "Pendiente de incorporar indicadores oficiales "
            "por localidad."
        )

    with tab2:
        st.info(
            "Aquí se calcularán las principales brechas "
            "territoriales."
        )

    with tab3:
        st.info(
            "FODA territorial pendiente de captura y validación."
        )

    with tab4:
        st.info(
            "Árbol de problemas pendiente de construcción."
        )


# =========================================================
# PLANEACIÓN
# =========================================================

def render_planeacion() -> None:
    st.header("📖 Planeación")

    localidad = st.session_state.get(
        "localidad_activa",
        LOCALIDAD_INICIAL,
    )

    st.subheader(localidad)

    st.write(
        "Diagnóstico → árbol de problemas → árbol de objetivos → "
        "alternativas → estrategias → líneas de acción → proyectos."
    )

    etapas = [
        "Diagnóstico territorial",
        "Problema central",
        "Árbol de problemas",
        "Árbol de objetivos",
        "Alternativas",
        "Estrategias",
        "Líneas de acción",
        "Proyecto / intervención",
    ]

    for numero, etapa in enumerate(
        etapas,
        start=1,
    ):
        st.markdown(
            f"**{numero}. {etapa}** — Pendiente"
        )


# =========================================================
# PbR / MIR
# =========================================================

def render_pbr_mir() -> None:
    st.header("💰 PbR / MIR")

    localidad = st.session_state.get(
        "localidad_activa",
        LOCALIDAD_INICIAL,
    )

    st.subheader(localidad)

    st.write(
        "Programas presupuestarios, MIR, indicadores, metas, "
        "fuentes de verificación y seguimiento SEGEMUN."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Programas",
        "Pendiente",
    )

    c2.metric(
        "Indicadores",
        "Pendiente",
    )

    c3.metric(
        "Metas",
        "Pendiente",
    )

    c4.metric(
        "Cumplimiento",
        "Pendiente",
    )


# =========================================================
# GESTIÓN VIVA
# =========================================================

def render_gestion() -> None:
    st.header("⚙️ Gestión Viva")

    localidad = st.session_state.get(
        "localidad_activa",
        LOCALIDAD_INICIAL,
    )

    st.subheader(localidad)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Presupuesto",
        "Pendiente",
    )

    c2.metric(
        "Proyectos",
        "Pendiente",
    )

    c3.metric(
        "Obras",
        "Pendiente",
    )

    c4.metric(
        "Resultados",
        "Pendiente",
    )

    st.divider()

    st.write(
        "Presupuesto → Ejercicio → Verificación → "
        "Beneficio real por localidad."
    )

    st.info(
        "Este módulo conectará planeación, presupuesto, "
        "ejecución física-financiera y evidencia."
    )


# =========================================================
# DATOS
# =========================================================

def render_datos() -> None:
    st.header("🗄️ Datos y calidad")

    localidades = cargar_localidades()

    st.write(
        "Fuentes previstas: INEGI, IGECEM, CONAPO, CONEVAL, "
        "DENUE, INE, IEEM, Data México, Plus Codes y "
        "trabajo de campo."
    )

    st.warning(
        "Los registros pendientes deben conservarse como "
        "pendientes. No se completarán mediante inferencias."
    )

    st.subheader("Catálogo actualmente cargado")

    st.dataframe(
        localidades,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"{len(localidades)} registros cargados de un universo "
        f"operativo de {TOTAL_LOCALIDADES_PDL} localidades."
    )


# =========================================================
# APLICACIÓN
# =========================================================

def render_app() -> None:
    """Renderiza la aplicación PDL completa."""

    st.set_page_config(
        page_title="PDL · Tejupilco",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "localidad_activa" not in st.session_state:
        st.session_state["localidad_activa"] = (
            LOCALIDAD_INICIAL
        )

    modulo = render_sidebar()

    render_header()

    vistas = {
        "Inicio": render_inicio,
        "Territorio": render_territorio,
        "Localidades": render_localidades,
        "Diagnóstico": render_diagnostico,
        "Planeación": render_planeacion,
        "PbR / MIR": render_pbr_mir,
        "Gestión Viva": render_gestion,
        "Datos": render_datos,
    }

    vista = vistas.get(modulo)

    if vista:
        vista()
    else:
        st.error(
            "No se encontró el módulo solicitado."
        )


if __name__ == "__main__":
    render_app()
