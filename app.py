from pathlib import Path
import py_compile

app_code = r'''from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import pydeck as pdk
import streamlit as st


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="PDL · Tejupilco",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

LOCALIDADES_CSV = DATA_DIR / "localidades_tejupilco_2025.csv"
GEO_CSV = DATA_DIR / "localidades_georef.csv"

RAW_CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Ente56298/pdl-tejupilco-streamlit/"
    "main/data/localidades_tejupilco_2025.csv"
)

LOCALIDAD_INICIAL = "Tejupilco de Hidalgo"

COLUMNAS_BASE = {
    "no",
    "localidad",
    "poblacion_total",
    "pct_del_total_municipal",
    "poblacion_femenina",
    "pct_femenino",
    "poblacion_masculina",
    "pct_masculino",
    "fuente",
}


# =========================================================
# ESTILO
# =========================================================

def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 14px;
            padding: 14px 16px;
            background: rgba(15, 23, 42, 0.24);
        }

        div[data-testid="stMetricLabel"] {
            font-weight: 600;
        }

        .pdl-flow {
            padding: 16px 18px;
            border-radius: 12px;
            border: 1px solid rgba(56, 189, 248, 0.28);
            background: rgba(14, 116, 144, 0.12);
            margin: 8px 0 18px 0;
        }

        .pdl-muted {
            opacity: .72;
            font-size: .92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DATOS
# =========================================================

@st.cache_data(ttl=3600)
def cargar_localidades() -> pd.DataFrame:
    """
    Carga la base de localidades del PDM Tejupilco 2025-2027.

    Prioridad:
    1. Archivo local incluido en el repositorio.
    2. Fallback al archivo RAW de GitHub.
    """

    if LOCALIDADES_CSV.exists():
        df = pd.read_csv(LOCALIDADES_CSV)
    else:
        try:
            df = pd.read_csv(RAW_CSV_URL)
        except Exception as exc:
            st.error(
                "No fue posible cargar `data/localidades_tejupilco_2025.csv` "
                "ni recuperar su copia desde GitHub."
            )
            st.exception(exc)
            st.stop()

    faltantes = COLUMNAS_BASE - set(df.columns)

    if faltantes:
        st.error(
            "El CSV no tiene la estructura esperada. "
            "Faltan las columnas: "
            + ", ".join(sorted(faltantes))
        )
        st.stop()

    df = df.copy()

    # Normalización nominal.
    df["localidad"] = df["localidad"].astype(str).str.strip()
    df["fuente"] = df["fuente"].astype(str).str.strip()

    # Conversión numérica segura.
    columnas_numericas = [
        "no",
        "poblacion_total",
        "pct_del_total_municipal",
        "poblacion_femenina",
        "pct_femenino",
        "poblacion_masculina",
        "pct_masculino",
    ]

    for columna in columnas_numericas:
        df[columna] = pd.to_numeric(df[columna], errors="coerce")

    # Identificador interno PDL.
    df["id_pdl"] = df["no"].apply(
        lambda valor: (
            f"PDL-TEJ-{int(valor):03d}"
            if pd.notna(valor)
            else "PDL-TEJ-PEND"
        )
    )

    # Cobertura del desglose por sexo.
    df["desglose_sexo_disponible"] = (
        df["poblacion_femenina"].notna()
        & df["poblacion_masculina"].notna()
    )

    # Consistencia aritmética cuando existen ambos datos.
    df["suma_sexo"] = (
        df["poblacion_femenina"].fillna(0)
        + df["poblacion_masculina"].fillna(0)
    )

    df["diferencia_sexo"] = df["poblacion_total"] - df["suma_sexo"]

    df.loc[
        ~df["desglose_sexo_disponible"],
        "diferencia_sexo",
    ] = pd.NA

    return df.sort_values("no").reset_index(drop=True)


@st.cache_data(ttl=3600)
def cargar_georreferencia() -> Optional[pd.DataFrame]:
    """
    Carga una capa opcional de georreferencia.

    Formatos aceptados:
    - no,lat,lon
    - localidad,lat,lon

    Mientras el archivo no exista, la aplicación sigue funcionando.
    """

    if not GEO_CSV.exists():
        return None

    geo = pd.read_csv(GEO_CSV)

    if not {"lat", "lon"}.issubset(geo.columns):
        return None

    geo = geo.copy()
    geo["lat"] = pd.to_numeric(geo["lat"], errors="coerce")
    geo["lon"] = pd.to_numeric(geo["lon"], errors="coerce")

    return geo


def integrar_georreferencia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Integra latitud/longitud si ya vienen en la base o si existe
    data/localidades_georef.csv.
    """

    base = df.copy()

    # Si el CSV principal ya tiene lat/lon, se respetan.
    if {"lat", "lon"}.issubset(base.columns):
        base["lat"] = pd.to_numeric(base["lat"], errors="coerce")
        base["lon"] = pd.to_numeric(base["lon"], errors="coerce")
        return base

    geo = cargar_georreferencia()

    if geo is None:
        base["lat"] = pd.NA
        base["lon"] = pd.NA
        return base

    if "no" in geo.columns:
        geo["no"] = pd.to_numeric(geo["no"], errors="coerce")
        columnas = ["no", "lat", "lon"]
        return base.merge(
            geo[columnas].drop_duplicates("no"),
            on="no",
            how="left",
        )

    if "localidad" in geo.columns:
        geo["localidad"] = geo["localidad"].astype(str).str.strip()
        columnas = ["localidad", "lat", "lon"]
        return base.merge(
            geo[columnas].drop_duplicates("localidad"),
            on="localidad",
            how="left",
        )

    base["lat"] = pd.NA
    base["lon"] = pd.NA
    return base


# =========================================================
# UTILIDADES
# =========================================================

def formato_entero(valor) -> str:
    if pd.isna(valor):
        return "Pendiente"
    return f"{int(valor):,}"


def formato_porcentaje(valor) -> str:
    if pd.isna(valor):
        return "Pendiente"
    return f"{float(valor):.1f} %"


def asegurar_localidad_activa(df: pd.DataFrame) -> None:
    nombres = df["localidad"].tolist()

    if not nombres:
        st.error("La base de localidades está vacía.")
        st.stop()

    actual = st.session_state.get("localidad_activa")

    if actual not in nombres:
        if LOCALIDAD_INICIAL in nombres:
            st.session_state["localidad_activa"] = LOCALIDAD_INICIAL
        else:
            st.session_state["localidad_activa"] = nombres[0]


def obtener_registro_activo(df: pd.DataFrame) -> pd.Series:
    asegurar_localidad_activa(df)

    localidad = st.session_state["localidad_activa"]

    coincidencias = df[df["localidad"] == localidad]

    if coincidencias.empty:
        return df.iloc[0]

    return coincidencias.iloc[0]


def ranking_poblacion(df: pd.DataFrame, localidad: str) -> Optional[int]:
    ranking = (
        df[["localidad", "poblacion_total"]]
        .sort_values("poblacion_total", ascending=False)
        .reset_index(drop=True)
    )

    posiciones = ranking.index[
        ranking["localidad"].eq(localidad)
    ].tolist()

    if not posiciones:
        return None

    return posiciones[0] + 1


# =========================================================
# SIDEBAR
# =========================================================

def render_sidebar(df: pd.DataFrame) -> str:
    asegurar_localidad_activa(df)

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

        nombres = df["localidad"].tolist()
        localidad_actual = st.session_state["localidad_activa"]

        indice = (
            nombres.index(localidad_actual)
            if localidad_actual in nombres
            else 0
        )

        localidad = st.selectbox(
            "Localidad activa",
            nombres,
            index=indice,
            key="selector_localidad_global",
        )

        st.session_state["localidad_activa"] = localidad

        registro = df[df["localidad"] == localidad].iloc[0]

        st.caption(
            f"{registro['id_pdl']} · "
            f"{formato_entero(registro['poblacion_total'])} hab."
        )

        st.divider()
        st.caption("Planeación de Desarrollo a nivel Localidad")

    return modulo


# =========================================================
# HEADER
# =========================================================

def render_header(df: pd.DataFrame) -> None:
    total_localidades = len(df)
    poblacion_total = int(df["poblacion_total"].fillna(0).sum())

    con_poblacion = int(df["poblacion_total"].notna().sum())
    cobertura_poblacion = (
        con_poblacion / total_localidades * 100
        if total_localidades
        else 0
    )

    con_sexo = int(df["desglose_sexo_disponible"].sum())

    cabecera = df[
        df["localidad"].eq("Tejupilco de Hidalgo")
    ]

    pct_cabecera = (
        float(cabecera.iloc[0]["pct_del_total_municipal"])
        if not cabecera.empty
        else None
    )

    st.title("PDL · Inteligencia Territorial Municipal")
    st.caption("Tejupilco · Estado de México")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Localidades",
        f"{total_localidades:,}",
    )

    c2.metric(
        "Población base",
        f"{poblacion_total:,}",
    )

    c3.metric(
        "Cobertura poblacional",
        f"{cobertura_poblacion:.1f} %",
    )

    c4.metric(
        "Desglose por sexo",
        f"{con_sexo}/{total_localidades}",
    )

    c5.metric(
        "Peso de la cabecera",
        formato_porcentaje(pct_cabecera),
    )

    st.divider()


# =========================================================
# INICIO
# =========================================================

def render_inicio(df: pd.DataFrame) -> None:
    st.header("Dashboard Vivo del Municipio")

    st.write(
        """
        Esta primera capa integra el universo de localidades y la estructura
        poblacional publicada en el PDM Tejupilco 2025-2027. Los módulos
        territoriales, de diagnóstico, planeación, PbR/MIR y gestión se
        conectarán progresivamente sobre la misma localidad activa.
        """
    )

    st.markdown(
        """
        <div class="pdl-flow">
        <b>Flujo rector:</b>
        Diagnóstico → Planeación → Presupuesto → Ejecución →
        Verificación → Resultado → nuevo diagnóstico.
        </div>
        """,
        unsafe_allow_html=True,
    )

    izquierda, derecha = st.columns([1.4, 1])

    with izquierda:
        st.subheader("Localidades con mayor población")

        top = (
            df.nlargest(10, "poblacion_total")
            [["localidad", "poblacion_total"]]
            .set_index("localidad")
        )

        st.bar_chart(top)

    with derecha:
        st.subheader("Lectura rápida")

        poblacion_total = int(df["poblacion_total"].sum())
        cabecera = df.loc[
            df["localidad"].eq("Tejupilco de Hidalgo"),
            "poblacion_total",
        ]

        poblacion_cabecera = (
            int(cabecera.iloc[0])
            if not cabecera.empty
            else 0
        )

        resto = poblacion_total - poblacion_cabecera

        st.metric(
            "Tejupilco de Hidalgo",
            f"{poblacion_cabecera:,}",
            "habitantes",
        )

        st.metric(
            "Resto de localidades",
            f"{resto:,}",
            "habitantes",
        )

        st.caption(
            "Los indicadores mostrados aquí proceden únicamente "
            "de la base poblacional actualmente cargada."
        )

    st.subheader("Arquitectura funcional")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.info("🔎\n\n**Diagnóstico**")
    c2.info("📖\n\n**Planeación**")
    c3.info("💰\n\n**PbR / MIR**")
    c4.info("⚙️\n\n**Gestión**")
    c5.info("📸\n\n**Evidencia**")


# =========================================================
# TERRITORIO
# =========================================================

def render_territorio(df: pd.DataFrame) -> None:
    st.header("🗺️ Territorio")

    territorial = integrar_georreferencia(df)

    geo = territorial.dropna(
        subset=["lat", "lon"]
    ).copy()

    col_mapa, col_capas = st.columns([4, 1], gap="large")

    with col_capas:
        st.subheader("Capas")

        localidades_on = st.checkbox(
            "Localidades",
            value=True,
        )

        st.checkbox(
            "Secciones electorales",
            value=False,
            disabled=True,
        )

        st.checkbox(
            "Carreteras",
            value=False,
            disabled=True,
        )

        st.checkbox(
            "Escuelas",
            value=False,
            disabled=True,
        )

        st.checkbox(
            "Salud",
            value=False,
            disabled=True,
        )

        st.checkbox(
            "DENUE",
            value=False,
            disabled=True,
        )

        st.checkbox(
            "Obras",
            value=False,
            disabled=True,
        )

        st.caption(
            "Las capas se activarán conforme se incorporen "
            "sus fuentes geoespaciales."
        )

    with col_mapa:
        if geo.empty:
            st.warning(
                "La base poblacional todavía no contiene coordenadas. "
                "El dashboard ya está preparado para usar "
                "`data/localidades_georef.csv` con columnas "
                "`no,lat,lon` o `localidad,lat,lon`."
            )

            st.info(
                "Mientras incorporamos la georreferencia oficial, "
                "el módulo Territorio conserva la segmentación por localidad "
                "sin inventar posiciones geográficas."
            )

            top = (
                territorial.nlargest(20, "poblacion_total")
                [
                    [
                        "id_pdl",
                        "localidad",
                        "poblacion_total",
                        "pct_del_total_municipal",
                    ]
                ]
            )

            st.dataframe(
                top,
                use_container_width=True,
                hide_index=True,
            )

        else:
            layers = []

            if localidades_on:
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=geo,
                        get_position="[lon, lat]",
                        get_radius=450,
                        radius_min_pixels=5,
                        radius_max_pixels=18,
                        get_fill_color="[0, 190, 190, 185]",
                        get_line_color="[255, 255, 255, 180]",
                        line_width_min_pixels=1,
                        stroked=True,
                        filled=True,
                        pickable=True,
                        auto_highlight=True,
                    )
                )

            lat_centro = float(geo["lat"].mean())
            lon_centro = float(geo["lon"].mean())

            deck = pdk.Deck(
                layers=layers,
                initial_view_state=pdk.ViewState(
                    latitude=lat_centro,
                    longitude=lon_centro,
                    zoom=9.2,
                    pitch=0,
                    bearing=0,
                ),
                tooltip={
                    "html": (
                        "<b>{localidad}</b><br/>"
                        "Población: {poblacion_total}<br/>"
                        "Participación municipal: "
                        "{pct_del_total_municipal}%"
                    ),
                    "style": {
                        "backgroundColor": "#0f172a",
                        "color": "white",
                    },
                },
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            st.caption(
                f"{len(geo)} localidades cuentan actualmente "
                "con coordenadas utilizables."
            )


# =========================================================
# LOCALIDADES
# =========================================================

def render_localidades(df: pd.DataFrame) -> None:
    st.header("📍 Localidades")

    registro = obtener_registro_activo(df)
    nombre = registro["localidad"]

    posicion = ranking_poblacion(df, nombre)

    st.subheader(nombre)
    st.caption(
        f"{registro['id_pdl']} · Fuente base: {registro['fuente']}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Población",
        formato_entero(registro["poblacion_total"]),
    )

    c2.metric(
        "Participación municipal",
        formato_porcentaje(
            registro["pct_del_total_municipal"]
        ),
    )

    c3.metric(
        "Ranking poblacional",
        (
            f"{posicion} de {len(df)}"
            if posicion is not None
            else "Pendiente"
        ),
    )

    c4.metric(
        "Desglose por sexo",
        (
            "Disponible"
            if bool(registro["desglose_sexo_disponible"])
            else "Parcial"
        ),
    )

    st.divider()

    izquierda, derecha = st.columns([1, 1])

    with izquierda:
        st.subheader("Composición poblacional")

        if bool(registro["desglose_sexo_disponible"]):
            composicion = pd.DataFrame(
                {
                    "Población": [
                        registro["poblacion_femenina"],
                        registro["poblacion_masculina"],
                    ]
                },
                index=["Mujeres", "Hombres"],
            )

            st.bar_chart(composicion)

            a, b = st.columns(2)

            a.metric(
                "Mujeres",
                formato_entero(
                    registro["poblacion_femenina"]
                ),
                formato_porcentaje(
                    registro["pct_femenino"]
                ),
            )

            b.metric(
                "Hombres",
                formato_entero(
                    registro["poblacion_masculina"]
                ),
                formato_porcentaje(
                    registro["pct_masculino"]
                ),
            )

        else:
            st.warning(
                "La fuente base no publica el conteo femenino y masculino "
                "para esta localidad."
            )

    with derecha:
        st.subheader("Ficha base")

        st.write(
            {
                "Número en la fuente": (
                    int(registro["no"])
                    if pd.notna(registro["no"])
                    else None
                ),
                "ID interno PDL": registro["id_pdl"],
                "Localidad": registro["localidad"],
                "Población total": (
                    int(registro["poblacion_total"])
                    if pd.notna(registro["poblacion_total"])
                    else None
                ),
                "% del total municipal": (
                    float(registro["pct_del_total_municipal"])
                    if pd.notna(
                        registro["pct_del_total_municipal"]
                    )
                    else None
                ),
            }
        )

        participacion = (
            float(registro["pct_del_total_municipal"]) / 100
            if pd.notna(
                registro["pct_del_total_municipal"]
            )
            else 0
        )

        st.progress(
            max(0.0, min(participacion, 1.0)),
            text="Peso relativo dentro de la población municipal",
        )


# =========================================================
# DIAGNÓSTICO
# =========================================================

def render_diagnostico(df: pd.DataFrame) -> None:
    st.header("📊 Diagnóstico por localidad")

    registro = obtener_registro_activo(df)
    nombre = registro["localidad"]

    st.subheader(nombre)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Población",
        formato_entero(registro["poblacion_total"]),
    )

    c2.metric(
        "Peso municipal",
        formato_porcentaje(
            registro["pct_del_total_municipal"]
        ),
    )

    c3.metric(
        "% femenino",
        formato_porcentaje(
            registro["pct_femenino"]
        ),
    )

    c4.metric(
        "% masculino",
        formato_porcentaje(
            registro["pct_masculino"]
        ),
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Base disponible",
            "Brechas",
            "FODA",
            "Árbol de problemas",
            "Evidencia",
        ]
    )

    with tab1:
        st.success(
            "Población total y participación municipal: disponibles."
        )

        if bool(registro["desglose_sexo_disponible"]):
            st.success(
                "Desglose femenino/masculino: disponible."
            )
        else:
            st.warning(
                "Desglose femenino/masculino: incompleto en la fuente."
            )

        st.info(
            "Pendiente de integrar: clave INEGI, coordenadas, vivienda, "
            "servicios, educación, salud, economía, marginación, "
            "accesibilidad, riesgos, infraestructura y geografía electoral."
        )

    with tab2:
        st.info(
            "La base poblacional por sí sola no permite identificar "
            "brechas de servicios o carencias. Este apartado se activará "
            "cuando se integren las fuentes sectoriales correspondientes."
        )

    with tab3:
        st.info(
            "FODA territorial pendiente de evidencia documental "
            "y levantamiento local."
        )

    with tab4:
        st.info(
            "Árbol de problemas pendiente. No se generará automáticamente "
            "a partir de población sin evidencia causal adicional."
        )

    with tab5:
        st.write("Fuente actualmente vinculada:")
        st.code(str(registro["fuente"]))


# =========================================================
# PLANEACIÓN
# =========================================================

def render_planeacion(df: pd.DataFrame) -> None:
    st.header("📖 Planeación")

    registro = obtener_registro_activo(df)
    st.subheader(registro["localidad"])

    st.markdown(
        """
        <div class="pdl-flow">
        Diagnóstico → Problema → Objetivo → Alternativas →
        Estrategia → Línea de acción → Proyecto.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "El CSV poblacional no contiene objetivos, estrategias, "
        "líneas de acción ni proyectos. El módulo está preparado "
        "para enlazarlos cuando se incorporen PDM, diagnóstico y "
        "matrices de planeación."
    )

    etapas = pd.DataFrame(
        {
            "Etapa": [
                "Diagnóstico territorial",
                "Problema central",
                "Árbol de problemas",
                "Árbol de objetivos",
                "Alternativas",
                "Estrategias",
                "Líneas de acción",
                "Proyecto / intervención",
            ],
            "Estado": ["Pendiente"] * 8,
        }
    )

    st.dataframe(
        etapas,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# PbR / MIR
# =========================================================

def render_pbr_mir(df: pd.DataFrame) -> None:
    st.header("💰 PbR / MIR")

    registro = obtener_registro_activo(df)
    st.subheader(registro["localidad"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Programas", "Pendiente")
    c2.metric("Indicadores", "Pendiente")
    c3.metric("Metas", "Pendiente")
    c4.metric("Cumplimiento", "Pendiente")

    st.info(
        "La fuente poblacional actual no contiene información PbR-SEGEMUN "
        "ni MIR. Estos valores permanecerán como pendientes hasta integrar "
        "programas presupuestarios, indicadores, metas y medios de verificación."
    )

    st.markdown(
        """
        **Cadena prevista**

        Diagnóstico territorial → Programa presupuestario →
        MIR → Indicador → Meta → Presupuesto →
        Ejecución → Evaluación.
        """
    )


# =========================================================
# GESTIÓN VIVA
# =========================================================

def render_gestion(df: pd.DataFrame) -> None:
    st.header("⚙️ Gestión Viva")

    registro = obtener_registro_activo(df)
    st.subheader(registro["localidad"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto", "Pendiente")
    c2.metric("Proyectos", "Pendiente")
    c3.metric("Obras", "Pendiente")
    c4.metric("Resultados", "Pendiente")

    st.markdown(
        """
        <div class="pdl-flow">
        Presupuesto → Ejercicio → Verificación →
        Beneficio real → Evidencia → Evaluación.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Este módulo se alimentará posteriormente con proyectos, obras, "
        "avance físico-financiero, fotografías, georreferencia y resultados."
    )


# =========================================================
# DATOS Y CALIDAD
# =========================================================

def render_datos(df: pd.DataFrame) -> None:
    st.header("🗄️ Datos y calidad")

    total = len(df)
    faltantes_sexo = int(
        (~df["desglose_sexo_disponible"]).sum()
    )

    poblacion_sin_desglose = int(
        df.loc[
            ~df["desglose_sexo_disponible"],
            "poblacion_total",
        ]
        .fillna(0)
        .sum()
    )

    fuentes = int(df["fuente"].nunique())

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Registros",
        f"{total:,}",
    )

    c2.metric(
        "Fuentes declaradas",
        f"{fuentes:,}",
    )

    c3.metric(
        "Sin conteo por sexo",
        f"{faltantes_sexo:,}",
    )

    c4.metric(
        "Población sin desglose",
        f"{poblacion_sin_desglose:,}",
    )

    st.subheader("Explorar catálogo")

    busqueda = st.text_input(
        "Buscar localidad",
        placeholder="Ej. Bejucos, Ixtapan, Rincón...",
    )

    max_pob = int(df["poblacion_total"].max())

    minimo = st.slider(
        "Población mínima",
        min_value=0,
        max_value=max_pob,
        value=0,
        step=max(1, max_pob // 200),
    )

    filtrado = df[
        df["poblacion_total"].fillna(0).ge(minimo)
    ].copy()

    if busqueda.strip():
        filtrado = filtrado[
            filtrado["localidad"].str.contains(
                busqueda.strip(),
                case=False,
                na=False,
            )
        ]

    columnas = [
        "id_pdl",
        "no",
        "localidad",
        "poblacion_total",
        "pct_del_total_municipal",
        "poblacion_femenina",
        "pct_femenino",
        "poblacion_masculina",
        "pct_masculino",
        "fuente",
    ]

    st.dataframe(
        filtrado[columnas],
        use_container_width=True,
        hide_index=True,
    )

    csv_export = filtrado[columnas].to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "Descargar selección CSV",
        data=csv_export,
        file_name="localidades_tejupilco_filtradas.csv",
        mime="text/csv",
    )

    with st.expander("Control de calidad"):
        st.write(
            f"- Localidades cargadas: **{total}**"
        )
        st.write(
            "- Localidades sin población total: "
            f"**{int(df['poblacion_total'].isna().sum())}**"
        )
        st.write(
            "- Localidades sin desglose femenino/masculino: "
            f"**{faltantes_sexo}**"
        )
        st.write(
            "- Habitantes asociados a registros sin desglose por sexo: "
            f"**{poblacion_sin_desglose:,}**"
        )

        inconsistencias = df[
            df["diferencia_sexo"].fillna(0).ne(0)
            & df["desglose_sexo_disponible"]
        ]

        st.write(
            "- Registros donde mujeres + hombres difiere de población total: "
            f"**{len(inconsistencias)}**"
        )

        if not inconsistencias.empty:
            st.dataframe(
                inconsistencias[
                    [
                        "localidad",
                        "poblacion_total",
                        "poblacion_femenina",
                        "poblacion_masculina",
                        "diferencia_sexo",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )


# =========================================================
# APLICACIÓN
# =========================================================

def render_app() -> None:
    aplicar_estilos()

    df = cargar_localidades()

    asegurar_localidad_activa(df)

    modulo = render_sidebar(df)

    render_header(df)

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

    if vista is None:
        st.error("No se encontró el módulo solicitado.")
        return

    vista(df)


if __name__ == "__main__":
    render_app()
'''

out = Path("/mnt/data/app.py")
out.write_text(app_code, encoding="utf-8")

# Validación sintáctica.
py_compile.compile(str(out), doraise=True)

print(f"app.py generado y validado: {out}")
print(f"Tamaño: {out.stat().st_size:,} bytes")
