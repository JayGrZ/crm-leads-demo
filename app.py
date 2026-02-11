import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection

# Configuración de página
st.set_page_config(page_title="CRM Lead Gen", page_icon="👥", layout="wide")

# --- Conexión Blindada ---
try:
    # Intenta conectar usando los Secrets de Streamlit Cloud
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Error de configuración: Asegúrate de haber puesto los 'Secrets' en el panel de Streamlit.")
    st.stop()

# --- Estilo Midnight ---
st.markdown(
    """
    <style>
    .stApp { background: #0E1117 !important; }
    [data-testid="stSidebar"] { background: #161B22 !important; }
    [data-testid="stSidebar"] [role="radiogroup"] input { display: none !important; }
    [data-testid="stSidebar"] [role="radio"] {
        display: block; padding: 0.5rem 0.75rem; margin: 2px 0;
        border-radius: 4px; border-left: 3px solid transparent; background: transparent;
    }
    [data-testid="stSidebar"] [role="radio"][aria-checked="true"] {
        background: rgba(255,255,255,0.08) !important; border-left-color: #58a6ff !important;
    }
    [data-testid="stDataFrame"] thead th { background: #21262d !important; color: #c9d1d9 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Funciones de Datos ---
def cargar_negocios():
    # Usamos la conexión establecida arriba
    r = conn.table("negocios").select("*").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def actualizar_estado(negocio_id: int, estado: str):
    conn.table("negocios").update({"estado": estado}).eq("id", negocio_id).execute()

CATEGORIAS = ["Bar", "Cafeterias", "Restaurantes"]
OPCIONES_ESTADO = ["🔴 Pendiente", "🟡 Llamando", "✅ Cita", "❌ No interesa"]

def normalizar_estado(val):
    v = str(val).strip() if pd.notna(val) else "🔴 Pendiente"
    if any(x in v for x in ["Llamando", "Llamado", "Re-llamar"]): return "🟡 Llamando"
    if "Cita" in v: return "✅ Cita"
    if "No interesa" in v: return "❌ No interesa"
    return "🔴 Pendiente"

# --- Lógica de la App ---
try:
    df_full = cargar_negocios()
except Exception as e:
    st.error(f"Error al cargar datos desde Supabase: {e}")
    st.stop()

if df_full.empty:
    st.warning("La base de datos está vacía.")
    st.stop()

# Limpieza rápida de datos
for col in ["barrio", "categoria", "estado"]:
    df_full[col] = df_full.get(col, pd.Series(dtype=object)).fillna("").astype(str)

df_full["estado"] = df_full["estado"].map(normalizar_estado)

# --- Interfaz ---
st.sidebar.markdown("## Menú")
seccion = st.sidebar.radio("Sección", options=["👥 Clientes", "⚙️ Administración"], label_visibility="collapsed")

if seccion == "👥 Clientes":
    st.markdown("## Gestión de Leads")
    categoria = st.radio("Categoría", options=CATEGORIAS, horizontal=True, label_visibility="collapsed")
    
    df = df_full[df_full["categoria"] == categoria].copy()
    
    if not df.empty:
        ids_tabla = df["id"].tolist()
        column_config = {
            "nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
            "telefono": st.column_config.TextColumn("Teléfono", width="large", disabled=True),
            "estado": st.column_config.SelectboxColumn("Estado", width="medium", options=OPCIONES_ESTADO, required=True),
        }
        
        edited = st.data_editor(
            df,
            column_order=["nombre", "telefono", "barrio", "estado"],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="editor"
        )

        if st.button("💾 Sincronizar Cambios"):
            for i in range(len(edited)):
                actualizar_estado(int(ids_tabla[i]), str(edited.iloc[i]["estado"]))
            st.success("¡Base de datos actualizada!")
            st.rerun()
    else:
        st.info(f"No hay registros para {categoria}")
else:
    st.write("Panel de administración.")