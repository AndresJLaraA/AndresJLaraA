import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN — edita solo esta sección
# ─────────────────────────────────────────────

# Nombre del archivo Excel (debe estar en la misma carpeta que app.py)
EXCEL_FILE = "Datos para Indicadores-FNTP-2025-264.xlsx"

HOJA = "Datos"
# ─────────────────────────────────────────────


@st.cache_data(ttl=300)   # refresca cada 5 minutos
def cargar_excel() -> pd.DataFrame:
    """Lee el Excel desde la misma carpeta que app.py."""
    ruta = Path(__file__).parent / EXCEL_FILE
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo '{EXCEL_FILE}' en la carpeta del proyecto.\n"
            f"Ruta buscada: {ruta}"
        )
    return pd.read_excel(ruta, sheet_name=HOJA, header=None)


def extraer_datos(df: pd.DataFrame) -> dict:
    """Parsea las tres secciones de la hoja Datos."""

    # ── Sección B: Curva-S (filas 120-130) ──────────────────────────────
    periodos   = ["Oct-25","Nov-25","Dic-25","Ene-26","Feb-26",
                  "Mar-26","Abr-26","May-26","Jun-26","Jul-26","Ago-26"]
    prog, real_s, desv, estados, montos = [], [], [], [], []

    for i in range(120, 131):
        row = df.iloc[i]
        prog.append(float(row[2]) * 100 if pd.notna(row[2]) else None)
        real_s.append(float(row[3]) * 100 if pd.notna(row[3]) else None)
        desv.append(float(row[4]) if pd.notna(row[4]) else None)
        estados.append(str(row[6]).strip() if pd.notna(row[6]) else "—")
        montos.append(float(row[5]) if pd.notna(row[5]) else None)

    presupuesto = float(df.iloc[118][2]) if pd.notna(df.iloc[118][2]) else 0

    curva = pd.DataFrame({
        "Período": periodos, "Programado": prog, "Real": real_s,
        "Desviación (pp)": desv, "Estado": estados, "Monto Ejec. COP": montos
    })

    # ── Sección A: IGs (filas 4-113, cada 11 filas = 1 IG) ──────────────
    ig_rows = []
    for i in range(4, 114, 11):
        row = df.iloc[i]
        ig_rows.append({
            "Cód.":        str(row[0]).strip(),
            "Indicador":   str(row[1]).strip(),
            "Unidad":      str(row[3]).strip(),
            "Meta Total":  float(row[4]) if pd.notna(row[4]) else 1,
            "Meta Acum.":  float(row[5]) if pd.notna(row[5]) else 0,
            "Período":     str(row[6]).strip() if pd.notna(row[6]) else "—",
            "Valor Real":  float(row[8]) if pd.notna(row[8]) else 0,
            "Últ. Acum.":  float(row[9]) if pd.notna(row[9]) else 0,
            "% Desempeño": float(row[10]) if pd.notna(row[10]) else 0,
            "Semáforo":    int(row[11]) if pd.notna(row[11]) else 1,
        })
    igs = pd.DataFrame(ig_rows)

    # ── Sección C: IRs (filas 135-178, cada 11 filas = 1 IR) ────────────
    ir_rows = []
    for i in range(135, 179, 11):
        row = df.iloc[i]
        ir_rows.append({
            "Cód.":       str(row[1]).strip(),
            "Indicador":  str(row[2]).strip(),
            "Unidad":     str(row[4]).strip(),
            "Meta":       row[5] if pd.notna(row[5]) else "—",
            "Valor":      float(row[8]) if pd.notna(row[8]) else 0,
            "Últ. Acum.": float(row[9]) if pd.notna(row[9]) else 0,
            "Fuente":     str(row[11]).strip() if pd.notna(row[11]) else "—",
        })
    irs = pd.DataFrame(ir_rows)

    return {"curva": curva, "igs": igs, "irs": irs, "presupuesto": presupuesto}


def semaforo_color(val: int) -> str:
    return {3: "🟢", 2: "🟡", 1: "🔴"}.get(val, "⚪")


def estado_color(estado: str) -> str:
    if "Rezagado" in estado:   return "🔴"
    if "Adelantado" in estado: return "🟢"
    if "En rango" in estado:   return "🟡"
    return "⚪"


# ════════════════════════════════════════════
#  LAYOUT
# ════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard FONTUR · FNTP-2025-264",
    layout="wide",
    page_icon="📊"
)

st.title("📊 Seguimiento Proyecto FNTP-2025-264")
st.caption("Campaña Colombia el País de la Belleza · FONTUR")

# ── Carga de datos ───────────────────────────
with st.spinner("Cargando datos desde la nube..."):
    try:
        df_raw = cargar_excel()
        datos  = extraer_datos(df_raw)
        curva  = datos["curva"]
        igs    = datos["igs"]
        irs    = datos["irs"]
        presupuesto = datos["presupuesto"]
        st.success(f"Datos actualizados · {datetime.now().strftime('%d/%m/%Y %H:%M')}", icon="✅")
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        st.info("Verifica que el archivo esté compartido públicamente y que el ID/URL sea correcto.")
        st.stop()

# ── KPIs ─────────────────────────────────────
corte = curva.dropna(subset=["Real"]).iloc[-1]
ejecucion_real = corte["Real"]
meta_mes       = corte["Programado"]
desviacion     = ejecucion_real - meta_mes
monto_ejec     = corte["Monto Ejec. COP"] or 0
igs_con_avance = int((igs["Valor Real"] > 0).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ejecución real acum.", f"{ejecucion_real:.1f}%",
            f"{desviacion:+.1f} pp vs programado",
            delta_color="normal" if desviacion >= 0 else "inverse")
col2.metric("Presupuesto total", f"${presupuesto/1e9:.1f}MM COP",
            f"Ejecutado: ${monto_ejec/1e9:.1f}MM")
col3.metric("IGs con avance", f"{igs_con_avance} / {len(igs)}",
            f"{len(igs)-igs_con_avance} en cero al corte",
            delta_color="off")
col4.metric("Estado general", corte["Estado"],
            f"Corte: {corte['Período']}", delta_color="off")

st.divider()

# ── Tabs ──────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Curva-S", "📋 Indicadores de Gestión (IGs)", "🎯 Indicadores de Resultado (IRs)"])

# ── TAB 1: Curva-S ────────────────────────────
with tab1:
    st.subheader("Curva-S — Avance presupuestal acumulado")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curva["Período"], y=curva["Programado"],
        name="Programado", mode="lines+markers",
        line=dict(color="#185FA5", width=2, dash="dot"),
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=curva.dropna(subset=["Real"])["Período"],
        y=curva.dropna(subset=["Real"])["Real"],
        name="Real ejecutado", mode="lines+markers",
        line=dict(color="#A32D2D", width=2.5),
        marker=dict(size=7)
    ))
    fig.update_layout(
        yaxis_title="% Acumulado",
        yaxis=dict(ticksuffix="%", range=[0, 110]),
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=20, b=40),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla detalle
    st.subheader("Detalle por período")
    tabla_curva = curva.copy()
    tabla_curva["Programado"] = tabla_curva["Programado"].map(lambda x: f"{x:.1f}%" if x else "—")
    tabla_curva["Real"]       = tabla_curva["Real"].map(lambda x: f"{x:.1f}%" if x else "—")
    tabla_curva["Desviación (pp)"] = tabla_curva["Desviación (pp)"].map(
        lambda x: f"{x:+.2f} pp" if x else "—")
    tabla_curva["Monto Ejec. COP"] = tabla_curva["Monto Ejec. COP"].map(
        lambda x: f"${x:,.0f}" if x else "—")
    tabla_curva["Estado"] = tabla_curva["Estado"].apply(
        lambda e: f"{estado_color(e)} {e}")
    st.dataframe(tabla_curva, use_container_width=True, hide_index=True)

# ── TAB 2: IGs ────────────────────────────────
with tab2:
    st.subheader("Indicadores de Gestión — Corte Feb-26")

    # Semáforo resumen
    verde    = int((igs["Semáforo"] == 3).sum())
    amarillo = int((igs["Semáforo"] == 2).sum())
    rojo     = int((igs["Semáforo"] == 1).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 En meta o adelantado", verde)
    c2.metric("🟡 En observación",       amarillo)
    c3.metric("🔴 Crítico / Sin avance", rojo)

    # Gráfico barras horizontales
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        y=igs["Cód."],
        x=igs["Meta Acum."] * 100,
        name="Meta acum.", orientation="h",
        marker_color="rgba(24,95,165,0.25)",
        text=[f"{v*100:.1f}%" for v in igs["Meta Acum."]],
        textposition="outside"
    ))
    fig2.add_trace(go.Bar(
        y=igs["Cód."],
        x=igs["Valor Real"] * 100,
        name="Real", orientation="h",
        marker_color=[
            "#3B6D11" if s == 3 else "#BA7517" if s == 2 else "#A32D2D"
            for s in igs["Semáforo"]
        ],
        text=[f"{v*100:.1f}%" for v in igs["Valor Real"]],
        textposition="outside"
    ))
    fig2.update_layout(
        barmode="overlay",
        xaxis=dict(ticksuffix="%", range=[0, 110]),
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=10, b=40, l=120),
        height=420
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Tabla IGs
    tabla_ig = igs.copy()
    tabla_ig["Sem."]       = tabla_ig["Semáforo"].map(semaforo_color)
    tabla_ig["Meta Acum."] = tabla_ig["Meta Acum."].map(lambda x: f"{x*100:.1f}%")
    tabla_ig["Valor Real"] = tabla_ig["Valor Real"].map(lambda x: f"{x*100:.1f}%")
    tabla_ig["% Desempeño"]= tabla_ig["% Desempeño"].map(lambda x: f"{x:.0f}%")
    st.dataframe(
        tabla_ig[["Cód.", "Indicador", "Unidad", "Meta Acum.", "Valor Real",
                  "% Desempeño", "Período", "Sem."]],
        use_container_width=True, hide_index=True
    )

# ── TAB 3: IRs ────────────────────────────────
with tab3:
    st.subheader("Indicadores de Resultado — Estado al corte")
    st.info("Los IRs se activan en períodos posteriores según cronograma. Todos en 0 al corte de Feb-26.")

    tabla_ir = irs.copy()
    tabla_ir["Estado"] = tabla_ir["Valor"].map(
        lambda v: "🟢 Con avance" if v > 0 else "⚪ Pendiente")
    st.dataframe(
        tabla_ir[["Cód.", "Indicador", "Unidad", "Meta", "Valor", "Estado", "Fuente"]],
        use_container_width=True, hide_index=True
    )

# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    st.markdown(f"""
    **Proyecto:** FNTP-2025-264  
    **Contrato:** FNTC-161-2026  
    **Horizonte:** Oct-25 – Ago-26  
    **Corte actual:** Feb-26 (Mes 5)  
    **Presupuesto:** ${presupuesto/1e9:.2f}MM COP  
    """)
    st.divider()
    if st.button("🔄 Forzar actualización"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Los datos se refrescan automáticamente cada 5 minutos.")
