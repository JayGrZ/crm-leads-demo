"""
CRM Lead Gen - Estilo Midnight. Navegación lateral sin botón azul, segmented control, tabla limpia.
"""
import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection

# ESTO ES LO IMPORTANTE:
# Si existen los secretos de Streamlit, los usa. 
# Si no, busca el .env (para cuando estés en local)
url = st.secrets["connections"]["supabase"]["url"]
key = st.secrets["connections"]["supabase"]["key"]

# Luego inicializas la conexión
conn = st.connection("supabase", type=SupabaseConnection)

from test_conexion import get_supabase_client

st.set_page_config(page_title="CRM Lead Gen", page_icon="👥", layout="wide")

# --- Estilo Midnight + navegación tipo VS Code (sin círculo azul, borde izquierdo) ---
st.markdown(
    """
    <style>
    /* Tema oscuro forzado */
    .stApp { background: #0E1117 !important; }
    [data-testid="stSidebar"] { background: #161B22 !important; }
    [data-testid="stSidebar"] .stMarkdown { color: #c9d1d9 !important; }
    
    /* Sidebar radio: sin círculo azul; opción seleccionada = fondo gris oscuro + borde izquierdo (VS Code) */
    [data-testid="stSidebar"] [role="radiogroup"] input { display: none !important; }
    [data-testid="stSidebar"] [role="radio"] {
        display: block;
        padding: 0.5rem 0.75rem;
        margin: 2px 0;
        border-radius: 4px;
        border-left: 3px solid transparent;
        background: transparent;
    }
    [data-testid="stSidebar"] [role="radio"][aria-checked="true"] {
        background: rgba(255,255,255,0.08) !important;
        border-left-color: #58a6ff !important;
    }
    [data-testid="stSidebar"] [role="radio"] label { color: #c9d1d9 !important; cursor: pointer; }
    [data-testid="stSidebar"] [role="radio"][aria-checked="true"] label { color: #f0f6fc !important; font-weight: 500; }
    
    /* Tabla: sin bordes innecesarios, encabezado más claro que el fondo */
    [data-testid="stDataFrame"] { border: none !important; }
    [data-testid="stDataFrame"] thead th {
        background: #21262d !important;
        color: #c9d1d9 !important;
        border: none !important;
        border-bottom: 1px solid #30363d !important;
    }
    [data-testid="stDataFrame"] tbody td { border: none !important; border-bottom: 1px solid #21262d !important; }
    [data-testid="stDataFrame"] { width: 100% !important; table-layout: fixed !important; }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { overflow: hidden; text-overflow: ellipsis; }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_resource
def get_client():
    return get_supabase_client()

def cargar_negocios():
    supabase = get_client()
    r = supabase.table("negocios").select("*").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def actualizar_estado(negocio_id: int, estado: str):
    get_client().table("negocios").update({"estado": estado}).eq("id", negocio_id).execute()

CATEGORIAS = ["Bar", "Cafeterias", "Restaurantes"]
OPCIONES_ESTADO = ["🔴 Pendiente", "🟡 Llamando", "✅ Cita", "❌ No interesa"]

def normalizar_estado(val):
    if pd.isna(val) or not str(val).strip():
        return "🔴 Pendiente"
    v = str(val).strip()
    if "Pendiente" in v or "Sin llamar" in v:
        return "🔴 Pendiente"
    if "Llamando" in v or "Llamado" in v or "Re-llamar" in v:
        return "🟡 Llamando"
    if "Cita" in v:
        return "✅ Cita"
    if "No interesa" in v:
        return "❌ No interesa"
    return "🔴 Pendiente"

# --- Datos ---
try:
    df_full = cargar_negocios()
except Exception as e:
    st.error(f"Error al conectar: {e}")
    st.stop()

if df_full.empty:
    st.warning("No hay negocios en la base de datos.")
    st.stop()

df_full["barrio"] = df_full.get("barrio", pd.Series(dtype=object)).fillna("").astype(str)
df_full["categoria"] = df_full.get("categoria", pd.Series(dtype=object)).fillna("").astype(str)
df_full["estado"] = df_full.get("estado", pd.Series(dtype=object)).fillna("Sin llamar").astype(str)
df_full["estado"] = df_full["estado"].map(normalizar_estado)
df_full["poblacion"] = pd.to_numeric(df_full.get("poblacion", 0), errors="coerce").fillna(0).astype(int)

# --- Sidebar: menú (radio con CSS tipo VS Code) ---
st.sidebar.markdown("## Menú")
seccion = st.sidebar.radio(
    "Sección",
    options=["👥 Clientes", "⚙️ Administración"],
    label_visibility="collapsed",
)

if seccion == "⚙️ Administración":
    st.info("Administración en desarrollo.")
    st.stop()

# --- Clientes: segmented control horizontal (st.radio horizontal) ---
st.markdown("## Clientes")
categoria = st.radio(
    "Categoría",
    options=CATEGORIAS,
    horizontal=True,
    label_visibility="collapsed",
    key="categoria",
)

df = df_full[df_full["categoria"] == categoria].copy()
df = df.sort_values("poblacion", ascending=False).reset_index(drop=True)

if df.empty:
    st.warning(f"No hay negocios con categoría **{categoria}**.")
    st.stop()

ids_tabla = df["id"].tolist()
column_order = ["nombre", "telefono", "barrio", "estado"]

# Anchos repartidos para ocupar ~100% y evitar scroll horizontal (medium = 1 parte, large = más)
column_config = {
    "nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
    "telefono": st.column_config.TextColumn("Teléfono", width="large", disabled=True),
    "barrio": st.column_config.TextColumn("Barrio", width="medium", disabled=True),
    "estado": st.column_config.SelectboxColumn("Estado", width="medium", options=OPCIONES_ESTADO, required=True),
}

edited = st.data_editor(
    df,
    column_order=column_order,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    key="editor",
)

if st.button("💾 Sincronizar Cambios"):
    if edited is not None and len(edited) == len(ids_tabla):
        for i in range(len(edited)):
            try:
                actualizar_estado(int(ids_tabla[i]), str(edited.iloc[i]["estado"]).strip())
            except Exception:
                pass
        st.success("Guardado.")
        st.rerun()
