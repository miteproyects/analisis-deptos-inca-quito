"""
🏢 Análisis de Precios de Departamentos — El Inca / San Isidro del Inca, Quito
Aplicación Streamlit con scraping multi-portal y visualización interactiva.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scraper import (
    recolectar_datos,
    generar_datos_realistas,
    haversine,
    CENTRO_LAT,
    CENTRO_LON,
    INCA_LAT,
    INCA_LON,
    SAN_ISIDRO_LAT,
    SAN_ISIDRO_LON,
)

# ──────────────────────────────────────────────
# Configuración de la página
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Análisis Inmobiliario — El Inca, Quito",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric > div {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown('<div class="main-header">🏢 Análisis de Precios — El Inca / San Isidro del Inca</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Departamentos en venta · Radio de 100m fuera del Inca · Quito, Ecuador</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Sidebar — Controles
# ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Quito_Panecillo.jpg/320px-Quito_Panecillo.jpg", use_container_width=True)
    st.markdown("### ⚙️ Configuración")

    fuente_datos = st.radio(
        "Fuente de datos:",
        ["🔄 Scraping en vivo (portales)", "📊 Datos de mercado (demo)"],
        index=1,
        help="El scraping consulta Properati, Plusvalía, iCasas y Terrenos.com en tiempo real."
    )

    st.markdown("---")
    st.markdown("### 🎯 Filtros de búsqueda")

    radio_busqueda = st.slider(
        "Radio de búsqueda (metros)",
        min_value=100, max_value=3000, value=1500, step=100,
        help="Radio alrededor del centro del Inca / San Isidro del Inca"
    )

    rango_precio = st.slider(
        "Rango de precio (USD)",
        min_value=20000, max_value=300000, value=(30000, 200000), step=5000
    )

    rango_anos = st.slider(
        "Año de construcción",
        min_value=1985, max_value=2026, value=(1990, 2026)
    )

    dormitorios_filtro = st.multiselect(
        "Dormitorios",
        options=[1, 2, 3, 4],
        default=[1, 2, 3, 4]
    )

    area_min, area_max = st.slider(
        "Área (m²)",
        min_value=20, max_value=250, value=(30, 200), step=5
    )

    st.markdown("---")
    st.markdown("### 📌 Fuentes de datos")
    st.markdown("""
    - [Properati](https://www.properati.com.ec)
    - [Plusvalía](https://www.plusvalia.com)
    - [iCasas](https://www.icasas.ec)
    - [Terrenos.com](https://www.terrenos.com)
    """)

# ──────────────────────────────────────────────
# Carga de datos
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_datos_scraping():
    return recolectar_datos(usar_scraping=True)

@st.cache_data(show_spinner=False)
def cargar_datos_demo():
    return generar_datos_realistas(n=200)

with st.spinner("Cargando datos inmobiliarios..."):
    if "Scraping" in fuente_datos:
        df_raw = cargar_datos_scraping()
    else:
        df_raw = cargar_datos_demo()

# ──────────────────────────────────────────────
# Aplicar filtros
# ──────────────────────────────────────────────
df = df_raw.copy()

# Filtro por radio
if "distancia_centro_m" in df.columns:
    df = df[df["distancia_centro_m"] <= radio_busqueda]

# Filtro por precio
df = df[(df["precio_usd"] >= rango_precio[0]) & (df["precio_usd"] <= rango_precio[1])]

# Filtro por año
if "ano_construccion" in df.columns:
    df = df[
        (df["ano_construccion"] >= rango_anos[0]) &
        (df["ano_construccion"] <= rango_anos[1])
    ]

# Filtro por dormitorios
if "dormitorios" in df.columns and dormitorios_filtro:
    df = df[df["dormitorios"].isin(dormitorios_filtro)]

# Filtro por área
if "area_m2" in df.columns:
    df = df[(df["area_m2"] >= area_min) & (df["area_m2"] <= area_max)]

# ──────────────────────────────────────────────
# Métricas principales
# ──────────────────────────────────────────────
st.markdown("---")

if len(df) == 0:
    st.warning("No se encontraron departamentos con los filtros seleccionados. Intenta ampliar los rangos.")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("🏠 Total listados", f"{len(df)}")
with col2:
    st.metric("💰 Precio promedio", f"${df['precio_usd'].mean():,.0f}")
with col3:
    st.metric("📐 Precio/m² prom.", f"${df['precio_m2'].mean():,.0f}" if "precio_m2" in df.columns and df["precio_m2"].notna().any() else "N/A")
with col4:
    st.metric("📏 Área promedio", f"{df['area_m2'].mean():,.0f} m²" if "area_m2" in df.columns else "N/A")
with col5:
    st.metric("🏗️ Año prom. constr.", f"{df['ano_construccion'].mean():,.0f}" if "ano_construccion" in df.columns else "N/A")

# ──────────────────────────────────────────────
# Tabs de análisis
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🗺️ Mapa", "📊 Año de Construcción", "💰 Análisis de Precios",
    "🏠 Características", "📈 Zona de Influencia",
    "🏨 Mi Departamento", "📣 Dónde Promocionar", "📋 Datos"
])

# ═══════════════════════════════════════════════
# TAB 1: MAPA INTERACTIVO
# ═══════════════════════════════════════════════
with tab1:
    st.subheader("Mapa de departamentos en venta")

    if "latitud" in df.columns and "longitud" in df.columns:
        df_map = df.dropna(subset=["latitud", "longitud"])

        fig_map = px.scatter_mapbox(
            df_map,
            lat="latitud",
            lon="longitud",
            color="precio_usd",
            size="area_m2" if "area_m2" in df_map.columns else None,
            hover_name="direccion",
            hover_data={
                "precio_usd": ":$,.0f",
                "area_m2": ":.0f",
                "dormitorios": True,
                "ano_construccion": True,
                "fuente": True,
                "latitud": False,
                "longitud": False,
            },
            color_continuous_scale="Viridis",
            size_max=15,
            zoom=14,
            mapbox_style="open-street-map",
            title="",
        )

        # Agregar círculo de radio de búsqueda
        import math
        circle_lats = []
        circle_lons = []
        for angle in range(0, 361, 5):
            dx = radio_busqueda * math.cos(math.radians(angle))
            dy = radio_busqueda * math.sin(math.radians(angle))
            circle_lats.append(CENTRO_LAT + (dy / 111320))
            circle_lons.append(CENTRO_LON + (dx / (111320 * math.cos(math.radians(CENTRO_LAT)))))

        fig_map.add_trace(go.Scattermapbox(
            lat=circle_lats,
            lon=circle_lons,
            mode="lines",
            line=dict(width=2, color="red"),
            name=f"Radio {radio_busqueda}m",
            showlegend=True,
        ))

        # Marcar centros
        fig_map.add_trace(go.Scattermapbox(
            lat=[INCA_LAT, SAN_ISIDRO_LAT],
            lon=[INCA_LON, SAN_ISIDRO_LON],
            mode="markers+text",
            marker=dict(size=12, color="red", symbol="star"),
            text=["El Inca", "San Isidro del Inca"],
            textposition="top center",
            name="Centros de referencia",
            showlegend=True,
        ))

        fig_map.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            coloraxis_colorbar=dict(title="Precio USD"),
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # Mapa de calor de precios por m²
        st.subheader("Mapa de calor — Precio por m²")
        if "precio_m2" in df_map.columns and df_map["precio_m2"].notna().any():
            fig_heat = px.density_mapbox(
                df_map.dropna(subset=["precio_m2"]),
                lat="latitud",
                lon="longitud",
                z="precio_m2",
                radius=20,
                zoom=14,
                mapbox_style="open-street-map",
                color_continuous_scale="YlOrRd",
            )
            fig_heat.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Los datos no contienen coordenadas geográficas para el mapa.")

# ═══════════════════════════════════════════════
# TAB 2: ANÁLISIS POR AÑO DE CONSTRUCCIÓN
# ═══════════════════════════════════════════════
with tab2:
    st.subheader("Análisis por Año de Construcción")

    if "ano_construccion" in df.columns and df["ano_construccion"].notna().any():
        col_a, col_b = st.columns(2)

        with col_a:
            # Distribución de años
            fig_hist = px.histogram(
                df, x="ano_construccion", nbins=20,
                title="Distribución de departamentos por año de construcción",
                color_discrete_sequence=["#667eea"],
                labels={"ano_construccion": "Año de construcción", "count": "Cantidad"},
            )
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_b:
            # Precio vs año
            fig_scatter = px.scatter(
                df, x="ano_construccion", y="precio_usd",
                color="dormitorios" if "dormitorios" in df.columns else None,
                size="area_m2" if "area_m2" in df.columns else None,
                title="Precio vs. Año de construcción",
                labels={
                    "ano_construccion": "Año de construcción",
                    "precio_usd": "Precio (USD)",
                    "dormitorios": "Dormitorios",
                    "area_m2": "Área m²",
                },
                trendline="lowess",
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Precio por m² vs año
        if "precio_m2" in df.columns and df["precio_m2"].notna().any():
            fig_pm2 = px.box(
                df.dropna(subset=["precio_m2"]),
                x=pd.cut(df.dropna(subset=["precio_m2"])["ano_construccion"],
                         bins=[1984, 1995, 2005, 2015, 2020, 2027],
                         labels=["1985-1995", "1996-2005", "2006-2015", "2016-2020", "2021-2026"]),
                y="precio_m2",
                title="Precio por m² según período de construcción",
                labels={"x": "Período", "precio_m2": "Precio/m² (USD)"},
                color_discrete_sequence=["#764ba2"],
            )
            st.plotly_chart(fig_pm2, use_container_width=True)

        # Tabla resumen por década
        st.subheader("Resumen por período de construcción")
        df_periodo = df.copy()
        df_periodo["periodo"] = pd.cut(
            df_periodo["ano_construccion"],
            bins=[1984, 1995, 2005, 2015, 2020, 2027],
            labels=["1985-1995", "1996-2005", "2006-2015", "2016-2020", "2021-2026"]
        )
        resumen = df_periodo.groupby("periodo", observed=True).agg(
            cantidad=("precio_usd", "count"),
            precio_promedio=("precio_usd", "mean"),
            precio_mediana=("precio_usd", "median"),
            precio_m2_prom=("precio_m2", "mean"),
            area_promedio=("area_m2", "mean"),
        ).round(0)
        resumen.columns = ["Cantidad", "Precio Prom. ($)", "Precio Mediana ($)", "$/m² Prom.", "Área Prom. (m²)"]
        st.dataframe(resumen, use_container_width=True)

    else:
        st.info("No hay datos de año de construcción disponibles.")

# ═══════════════════════════════════════════════
# TAB 3: ANÁLISIS DE PRECIOS
# ═══════════════════════════════════════════════
with tab3:
    st.subheader("Análisis detallado de precios")

    col_c, col_d = st.columns(2)

    with col_c:
        # Distribución de precios
        fig_precio = px.histogram(
            df, x="precio_usd", nbins=30,
            title="Distribución de precios",
            color_discrete_sequence=["#f093fb"],
            labels={"precio_usd": "Precio (USD)", "count": "Cantidad"},
        )
        fig_precio.add_vline(x=df["precio_usd"].mean(), line_dash="dash", line_color="red",
                             annotation_text=f"Media: ${df['precio_usd'].mean():,.0f}")
        fig_precio.add_vline(x=df["precio_usd"].median(), line_dash="dot", line_color="blue",
                             annotation_text=f"Mediana: ${df['precio_usd'].median():,.0f}")
        st.plotly_chart(fig_precio, use_container_width=True)

    with col_d:
        # Precio por m²
        if "precio_m2" in df.columns and df["precio_m2"].notna().any():
            fig_pm2_hist = px.histogram(
                df.dropna(subset=["precio_m2"]), x="precio_m2", nbins=30,
                title="Distribución de precio por m²",
                color_discrete_sequence=["#4facfe"],
                labels={"precio_m2": "Precio/m² (USD)", "count": "Cantidad"},
            )
            st.plotly_chart(fig_pm2_hist, use_container_width=True)

    # Precio vs Área
    if "area_m2" in df.columns:
        fig_area = px.scatter(
            df, x="area_m2", y="precio_usd",
            color="dormitorios" if "dormitorios" in df.columns else None,
            title="Precio vs. Área del departamento",
            labels={"area_m2": "Área (m²)", "precio_usd": "Precio (USD)", "dormitorios": "Dormitorios"},
            trendline="ols",
        )
        st.plotly_chart(fig_area, use_container_width=True)

    # Box plot por fuente
    if "fuente" in df.columns:
        fig_fuente = px.box(
            df, x="fuente", y="precio_usd",
            title="Distribución de precios por portal inmobiliario",
            labels={"fuente": "Portal", "precio_usd": "Precio (USD)"},
            color="fuente",
        )
        st.plotly_chart(fig_fuente, use_container_width=True)

# ═══════════════════════════════════════════════
# TAB 4: CARACTERÍSTICAS FÍSICAS
# ═══════════════════════════════════════════════
with tab4:
    st.subheader("Análisis por características del departamento")

    col_e, col_f = st.columns(2)

    with col_e:
        if "dormitorios" in df.columns:
            fig_dorm = px.box(
                df, x="dormitorios", y="precio_usd",
                title="Precio según número de dormitorios",
                labels={"dormitorios": "Dormitorios", "precio_usd": "Precio (USD)"},
                color="dormitorios",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig_dorm, use_container_width=True)

    with col_f:
        if "banos" in df.columns:
            fig_banos = px.box(
                df, x="banos", y="precio_usd",
                title="Precio según número de baños",
                labels={"banos": "Baños", "precio_usd": "Precio (USD)"},
                color="banos",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig_banos, use_container_width=True)

    col_g, col_h = st.columns(2)

    with col_g:
        if "parqueaderos" in df.columns:
            fig_parq = px.violin(
                df, x="parqueaderos", y="precio_usd",
                title="Precio según parqueaderos",
                labels={"parqueaderos": "Parqueaderos", "precio_usd": "Precio (USD)"},
                color="parqueaderos",
                box=True,
            )
            st.plotly_chart(fig_parq, use_container_width=True)

    with col_h:
        if "piso" in df.columns:
            fig_piso = px.scatter(
                df, x="piso", y="precio_m2" if "precio_m2" in df.columns else "precio_usd",
                title="Precio/m² según piso del departamento",
                labels={
                    "piso": "Piso",
                    "precio_m2": "Precio/m² (USD)",
                    "precio_usd": "Precio (USD)",
                },
                trendline="lowess",
                color="dormitorios" if "dormitorios" in df.columns else None,
            )
            st.plotly_chart(fig_piso, use_container_width=True)

    # Matriz de correlación
    st.subheader("Matriz de correlación entre variables")
    numeric_cols = ["precio_usd", "precio_m2", "area_m2", "dormitorios", "banos",
                    "parqueaderos", "ano_construccion", "piso", "distancia_centro_m"]
    numeric_cols = [c for c in numeric_cols if c in df.columns and df[c].notna().any()]

    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            title="Correlación entre variables",
            labels=dict(color="Correlación"),
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)

# ═══════════════════════════════════════════════
# TAB 5: ZONA DE INFLUENCIA
# ═══════════════════════════════════════════════
with tab5:
    st.subheader("Análisis por zona de influencia")

    if "zona_influencia" in df.columns and "distancia_centro_m" in df.columns:
        col_i, col_j = st.columns(2)

        with col_i:
            zona_counts = df["zona_influencia"].value_counts().reset_index()
            zona_counts.columns = ["Zona", "Cantidad"]
            fig_zona = px.pie(
                zona_counts, names="Zona", values="Cantidad",
                title="Distribución por zona de influencia",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4,
            )
            st.plotly_chart(fig_zona, use_container_width=True)

        with col_j:
            fig_zona_precio = px.box(
                df, x="zona_influencia", y="precio_m2" if "precio_m2" in df.columns else "precio_usd",
                title="Precio/m² por zona de influencia",
                labels={
                    "zona_influencia": "Zona",
                    "precio_m2": "Precio/m² (USD)",
                    "precio_usd": "Precio (USD)",
                },
                color="zona_influencia",
            )
            st.plotly_chart(fig_zona_precio, use_container_width=True)

        # Precio vs distancia
        fig_dist = px.scatter(
            df, x="distancia_centro_m", y="precio_m2" if "precio_m2" in df.columns else "precio_usd",
            color="zona_influencia",
            title="Relación precio/m² vs. distancia al centro del Inca",
            labels={
                "distancia_centro_m": "Distancia al centro (m)",
                "precio_m2": "Precio/m² (USD)",
                "precio_usd": "Precio (USD)",
                "zona_influencia": "Zona",
            },
            trendline="lowess",
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        # Resumen por zona
        st.subheader("Resumen por zona de influencia")
        resumen_zona = df.groupby("zona_influencia").agg(
            cantidad=("precio_usd", "count"),
            precio_prom=("precio_usd", "mean"),
            precio_m2_prom=("precio_m2", "mean") if "precio_m2" in df.columns else ("precio_usd", "mean"),
            area_prom=("area_m2", "mean"),
            dist_prom=("distancia_centro_m", "mean"),
        ).round(0)
        resumen_zona.columns = ["Cantidad", "Precio Prom. ($)", "$/m² Prom.", "Área Prom. (m²)", "Dist. Prom. (m)"]
        st.dataframe(resumen_zona, use_container_width=True)

    else:
        st.info("No hay datos de zona de influencia disponibles.")

# ═══════════════════════════════════════════════
# TAB 6: MI DEPARTAMENTO — Análisis Personalizado
# ═══════════════════════════════════════════════
with tab6:
    st.subheader("🏨 Análisis de tu departamento — Las Cucardas y Madreselvas")

    st.markdown("""
    **Ubicación:** Calle De las Cucardas y Madreselvas, Kennedy, San Isidro del Inca
    **Características:** 92 m² cubiertos · Terraza comunal · 1 parqueadero
    """)

    # Datos del departamento del usuario
    MI_AREA = 92
    MI_PARQ = 1
    MI_LAT = -0.1465
    MI_LON = -0.4765

    # Departamentos comparables
    comparables = df[
        (df["area_m2"].between(MI_AREA - 20, MI_AREA + 20)) &
        (df["parqueaderos"] >= 0)
    ].copy()

    if len(comparables) > 0:
        precio_m2_mercado = comparables["precio_m2"].median()
        precio_estimado = MI_AREA * precio_m2_mercado
        precio_min = comparables["precio_usd"].quantile(0.25)
        precio_max = comparables["precio_usd"].quantile(0.75)

        col_mi1, col_mi2, col_mi3 = st.columns(3)
        with col_mi1:
            st.metric("💰 Precio estimado de tu depto.", f"${precio_estimado:,.0f}")
        with col_mi2:
            st.metric("📊 Rango de mercado", f"${precio_min:,.0f} — ${precio_max:,.0f}")
        with col_mi3:
            st.metric("📐 Precio/m² zona", f"${precio_m2_mercado:,.0f}/m²")

        st.markdown("---")
        st.markdown("#### Posición de tu departamento en el mercado")

        fig_comp = px.histogram(
            comparables, x="precio_usd", nbins=20,
            title="Tu departamento vs. mercado de comparables (±20 m²)",
            labels={"precio_usd": "Precio (USD)", "count": "Cantidad"},
            color_discrete_sequence=["#a8d8ea"],
        )
        fig_comp.add_vline(
            x=precio_estimado, line_dash="dash", line_color="red", line_width=3,
            annotation_text=f"Tu depto: ${precio_estimado:,.0f}",
            annotation_font_color="red",
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Análisis de refacción
        st.markdown("---")
        st.markdown("#### 🔧 ¿Refaccionar o dejar como está?")

        if "ano_construccion" in comparables.columns:
            nuevos = comparables[comparables["ano_construccion"] >= 2018]
            antiguos = comparables[comparables["ano_construccion"] < 2018]

            if len(nuevos) > 0 and len(antiguos) > 0:
                delta_precio_m2 = nuevos["precio_m2"].median() - antiguos["precio_m2"].median()
                delta_total = delta_precio_m2 * MI_AREA

                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    fig_refac = go.Figure()
                    fig_refac.add_trace(go.Bar(
                        name="Deptos antiguos (<2018)",
                        x=["Precio/m²"],
                        y=[antiguos["precio_m2"].median()],
                        marker_color="#ff9999",
                    ))
                    fig_refac.add_trace(go.Bar(
                        name="Deptos nuevos/remodelados (≥2018)",
                        x=["Precio/m²"],
                        y=[nuevos["precio_m2"].median()],
                        marker_color="#66b3ff",
                    ))
                    fig_refac.update_layout(
                        title="Diferencia de precio: remodelado vs. sin remodelar",
                        barmode="group",
                        yaxis_title="USD/m²",
                    )
                    st.plotly_chart(fig_refac, use_container_width=True)

                with col_r2:
                    st.markdown("##### Análisis de rentabilidad de refacción")

                    costo_refaccion_m2 = 150
                    costo_total_refac = costo_refaccion_m2 * MI_AREA

                    if delta_total > costo_total_refac:
                        roi = ((delta_total - costo_total_refac) / costo_total_refac) * 100
                        st.success(f"""
                        ✅ **Se recomienda refaccionar**

                        - **Ganancia potencial por refacción:** ${delta_total:,.0f}
                        - **Costo estimado de refacción:** ${costo_total_refac:,.0f}
                        - **ROI estimado:** {roi:.0f}%
                        - **Diferencia $/m²:** ${delta_precio_m2:,.0f}/m²

                        Una refacción moderada (pintura, pisos, cocina, baños)
                        podría aumentar significativamente el valor de venta.
                        """)
                    else:
                        st.info(f"""
                        ℹ️ **Opcional refaccionar**

                        - **Ganancia potencial:** ${delta_total:,.0f}
                        - **Costo estimado:** ${costo_total_refac:,.0f}

                        La diferencia de precio no justifica una refacción completa.
                        Considera mejoras cosméticas puntuales (pintura, limpieza profunda).
                        """)

        # Tiempo estimado de venta
        st.markdown("---")
        st.markdown("#### ⏱️ Tiempo estimado de venta")
        st.markdown("""
        Según el análisis del mercado en la zona del Inca / San Isidro del Inca:

        - **Departamentos con precio competitivo** (percentil 25-50): 30-60 días
        - **Departamentos a precio de mercado** (mediana): 60-120 días
        - **Departamentos sobre el mercado** (percentil 75+): 120-180+ días

        Para tu departamento de 92 m² con terraza comunal y 1 parqueadero,
        un precio en el rango competitivo maximizaría la velocidad de venta.
        """)

    else:
        st.warning("No hay suficientes datos comparables para analizar tu departamento.")

# ═══════════════════════════════════════════════
# TAB 7: DÓNDE PROMOCIONAR
# ═══════════════════════════════════════════════
with tab7:
    st.subheader("📣 Estrategia de promoción para tu departamento")

    st.markdown("""
    **Tu departamento:** 92 m² · Terraza comunal · 1 parqueadero
    **Ubicación:** Las Cucardas y Madreselvas, Kennedy, San Isidro del Inca
    """)

    st.markdown("---")

    # Ranking de portales
    st.markdown("#### 🏆 Ranking de portales recomendados")

    portales_data = {
        "Portal": [
            "Plusvalía", "Properati", "iCasas / Trovit",
            "MercadoLibre Inmuebles", "Facebook Marketplace",
            "Grupos WhatsApp inmobiliarios", "Instagram Reels/Stories"
        ],
        "Alcance en Quito": ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐"],
        "Costo": ["Gratuito/Premium", "Gratuito", "Gratuito", "Gratuito", "Gratuito", "Gratuito", "Gratuito"],
        "Tipo de comprador": [
            "Profesional / Inversionista",
            "Profesional / Clase media-alta",
            "Agregador (llega a múltiples portales)",
            "Comprador general",
            "Comprador directo / local",
            "Red de contactos / agentes",
            "Comprador joven / millennial",
        ],
        "Prioridad": ["🔴 ALTA", "🔴 ALTA", "🟡 MEDIA", "🟡 MEDIA", "🔴 ALTA", "🟡 MEDIA", "🟡 MEDIA"],
    }
    df_portales = pd.DataFrame(portales_data)
    st.dataframe(df_portales, use_container_width=True, hide_index=True)

    st.markdown("---")

    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("#### 🎯 Estrategia recomendada")
        st.markdown("""
        **Paso 1 — Portales principales (Semana 1):**
        - Publicar en **Plusvalía** (mayor tráfico inmobiliario en Ecuador)
        - Publicar en **Properati** (buen posicionamiento SEO)
        - Publicar en **Facebook Marketplace** (alcance masivo y gratuito)

        **Paso 2 — Amplificación (Semana 2):**
        - Publicar en **iCasas** (replica en Trovit y Mitula automáticamente)
        - Publicar en **MercadoLibre Inmuebles**
        - Compartir en grupos de WhatsApp del sector Inca/Kennedy

        **Paso 3 — Redes sociales (Continuo):**
        - Video corto del departamento en **Instagram Reels**
        - Publicar en grupos de Facebook: "Departamentos en venta Quito Norte"
        - Contactar 2-3 agentes inmobiliarios de la zona
        """)

    with col_p2:
        st.markdown("#### 📸 Tips para el anuncio")
        st.markdown("""
        **Fotos profesionales** son clave para vender rápido:
        - Tomar fotos con luz natural (mañana, 9-11 AM)
        - Mínimo 10-15 fotos de calidad
        - Incluir: sala, cocina, dormitorios, baños, terraza, parqueadero
        - Foto aérea/exterior del edificio

        **Título del anuncio sugerido:**
        > "Departamento 92m² con terraza — San Isidro del Inca, Sector Kennedy"

        **Destacar:**
        - Terraza comunal (valor agregado)
        - Parqueadero incluido
        - Cercanía a la Embajada Americana
        - Transporte público accesible
        - Zona residencial tranquila con comercios
        """)

    st.markdown("---")

    # Análisis comparativo de portales
    if "fuente" in df.columns:
        st.markdown("#### 📊 Distribución de listados por portal en la zona")
        fuente_counts = df["fuente"].value_counts().reset_index()
        fuente_counts.columns = ["Portal", "Listados"]
        fig_portales = px.bar(
            fuente_counts, x="Portal", y="Listados",
            title="Cantidad de listados activos por portal",
            color="Portal",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_portales, use_container_width=True)

    # Precio sugerido
    st.markdown("---")
    st.markdown("#### 💰 Precio sugerido de publicación")
    comparables_promo = df[df["area_m2"].between(MI_AREA - 15, MI_AREA + 15)].copy() if "area_m2" in df.columns else df.copy()
    if len(comparables_promo) > 0:
        p_rapido = comparables_promo["precio_usd"].quantile(0.30)
        p_mercado = comparables_promo["precio_usd"].median()
        p_alto = comparables_promo["precio_usd"].quantile(0.70)

        col_pr1, col_pr2, col_pr3 = st.columns(3)
        with col_pr1:
            st.metric("🚀 Venta rápida (30-45 días)", f"${p_rapido:,.0f}",
                      help="Precio agresivo para vender en menos de 45 días")
        with col_pr2:
            st.metric("⚖️ Precio de mercado (60-90 días)", f"${p_mercado:,.0f}",
                      help="Precio alineado con la mediana del mercado")
        with col_pr3:
            st.metric("📈 Precio aspiracional (90-150 días)", f"${p_alto:,.0f}",
                      help="Precio por encima del mercado, toma más tiempo")

# ═══════════════════════════════════════════════
# TAB 8: DATOS CRUDOS
# ═══════════════════════════════════════════════
with tab8:
    st.subheader("Datos completos")

    # Estadísticas descriptivas
    st.markdown("#### Estadísticas descriptivas")
    desc_cols = ["precio_usd", "precio_m2", "area_m2", "dormitorios", "banos",
                 "parqueaderos", "ano_construccion", "piso"]
    desc_cols = [c for c in desc_cols if c in df.columns]
    st.dataframe(df[desc_cols].describe().round(2), use_container_width=True)

    st.markdown("#### Listado completo")
    display_cols = [c for c in ["fuente", "precio_usd", "precio_m2", "area_m2", "dormitorios",
                                "banos", "parqueaderos", "ano_construccion", "piso",
                                "direccion", "zona_influencia", "distancia_centro_m"]
                    if c in df.columns]

    st.dataframe(
        df[display_cols].sort_values("precio_usd", ascending=False),
        use_container_width=True,
        height=500,
    )

    # Descargar CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar datos como CSV",
        data=csv,
        file_name="departamentos_inca_quito.csv",
        mime="text/csv",
    )

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.85rem;">
        📊 Análisis Inmobiliario — El Inca / San Isidro del Inca, Quito, Ecuador<br>
        Fuentes: Properati · Plusvalía · iCasas · Terrenos.com<br>
        Desarrollado con Streamlit + Python · 2026
    </div>
    """,
    unsafe_allow_html=True,
)

