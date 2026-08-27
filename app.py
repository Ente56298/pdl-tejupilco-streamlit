import streamlit as st
import pandas as pd
import pydeck as pdk


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
        st.caption("Planeación de Desarrollo a nivel Localidad")

    return modulo


def render_header() -> None:
    st.title("PDL · Inteligencia Territorial Municipal")
    st.caption("Tejupilco · Estado de México")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Localidades", "149")
    c2.metric("Con datos", "5")
    c3.metric("Pendientes", "144")
    c4.metric("Avance", "3.4 %")

    st.divider()


def render_inicio() -> None:
    st.header("Dashboard Vivo del Municipio")
    st.write(
        """
        El PDL integra territorio, indicadores, diagnóstico por localidad,
        planeación, PbR-SEGEMUN, MIR, proyectos, gestión, evaluación y evidencia.
        """
    )

    st.info(
        "Flujo rector: Diagnóstico → Planeación → Presupuesto → "
        "Ejecución → Verificación → Resultado."
    )


def render_territorio() -> None:
    st.header("🗺️ Territorio")

    localidades = pd.DataFrame(
        {
            "localidad": [
                "Tejupilco de Hidalgo",
                "Bejucos",
                "San Andrés Ocotepec",
                "Santo Domingo-Zacatepec",
                "Rincón de Aguirre",
            ],
            "lat": [18.905, 18.815, 18.940, 18.895, 18.900],
            "lon": [-100.153, -100.420, -100.105, -100.170, -100.120],
            "poblacion": [30967, 2437, 1826, 3220, 1700],
        }
    )

    col_mapa, col_capas = st.columns([4, 1])

    with col_capas:
        st.subheader("Capas")
        localidades_on = st.checkbox("Localidades", True)
        st.checkbox("Secciones electorales", False)
        st.checkbox("Carreteras", False)
        st.checkbox("Escuelas", False)
        st.checkbox("Salud", False)
        st.checkbox("DENUE", False)
        st.checkbox("Obras", False)

    layers = []

    if localidades_on:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=localidades,
                get_position="[lon, lat]",
                get_radius=450,
                get_fill_color="[0, 180, 180, 180]",
                pickable=True,
            )
        )

    view = pdk.ViewState(
        latitude=18.90,
        longitude=-100.18,
        zoom=9.2,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip={
            "html": "<b>{localidad}</b><br/>Población: {poblacion}",
            "style": {"backgroundColor": "#0f172a", "color": "white"},
        },
    )

    with col_mapa:
        st.pydeck_chart(deck, use_container_width=True)

    st.caption(
        "MVP cartográfico. Las siguientes versiones sustituirán estos puntos "
        "de demostración por capas oficiales GeoJSON/PostGIS."
    )


def render_localidades() -> None:
    st.header("📍 Localidades")
    st.write(
        "Catálogo maestro, fichas territoriales y comparación entre localidades."
    )

    localidad = st.selectbox(
        "Localidad activa",
        [
            "Tejupilco de Hidalgo",
            "Bejucos",
            "San Andrés Ocotepec",
            "Santo Domingo-Zacatepec",
            "Rincón de Aguirre",
        ],
    )

    st.session_state["localidad_activa"] = localidad
    st.success(f"Localidad seleccionada: {localidad}")


def render_diagnostico() -> None:
    st.header("📊 Diagnóstico")
    localidad = st.session_state.get("localidad_activa", "Tejupilco de Hidalgo")
    st.subheader(localidad)
    st.write("Indicadores, brechas, análisis situacional, FODA y árboles.")


def render_planeacion() -> None:
    st.header("📖 Planeación")
    st.write(
        "Diagnóstico → árbol de problemas → árbol de objetivos → "
        "estrategias → líneas de acción → proyectos."
    )


def render_pbr_mir() -> None:
    st.header("💰 PbR / MIR")
    st.write(
        "Programas presupuestarios, MIR, indicadores, metas, fuentes de "
        "verificación y seguimiento SEGEMUN."
    )


def render_gestion() -> None:
    st.header("⚙️ Gestión Viva")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto", "Pendiente")
    c2.metric("Proyectos", "Pendiente")
    c3.metric("Obras", "Pendiente")
    c4.metric("Resultados", "Pendiente")

    st.write(
        "Presupuesto → Ejercicio → Verificación → Beneficio real por localidad."
    )


def render_datos() -> None:
    st.header("🗄️ Datos y calidad")
    st.write(
        "Fuentes previstas: INEGI, IGECEM, CONAPO, CONEVAL, DENUE, "
        "INE, IEEM, Data México, Plus Codes y trabajo de campo."
    )

    st.warning(
        "Los registros pendientes deben conservarse como pendientes; "
        "no se completarán mediante inferencias."
    )


def render_app() -> None:
    """Renderiza la aplicación PDL completa."""
    st.set_page_config(
        page_title="PDL · Tejupilco",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "localidad_activa" not in st.session_state:
        st.session_state["localidad_activa"] = "Tejupilco de Hidalgo"

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

    vistas[modulo]()


if __name__ == "__main__":
    render_app()
