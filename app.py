import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# Configuración de página
st.set_page_config(page_title="CRM Lead Gen", page_icon="👥", layout="wide")

# --- CONEXIÓN BLINDADA ---
try:
    # Intenta leer de la sección [connections.supabase] o directamente de los secretos raíz
    if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        s_url = st.secrets["connections"]["supabase"]["url"]
        s_key = st.secrets["connections"]["supabase"]["key"]
    else:
        # Por si los pusiste sin el encabezado [connections.supabase]
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
    
    conn = st.connection("supabase", type=SupabaseConnection, url=s_url, key=s_key)
except Exception as e:
    st.error(f"Error crítico de conexión. Revisa los Secrets de Streamlit.")
    st.info("Asegúrate de que en el panel de Secrets de Streamlit estén definidos SUPABASE_URL y SUPABASE_KEY")
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
    st.error(f"Error al cargar datos: {e}")
    st.stop()

if df_full.empty:
    st.warning("La base de datos está vacía.")
    st.stop()

# --- Interfaz ---
st.sidebar.markdown("## Menú")
seccion = st.sidebar.radio("Sección", options=["👥 Clientes", "⚙️ Administración"], label_visibility="collapsed")

if seccion == "👥 Clientes":
    st.markdown("## Gestión de Leads")
    categoria = st.radio("Categoría", options=CATEGORIAS, horizontal=True, label_visibility="collapsed")
    
    # 1. Filtramos y ORDENAMOS por población (Mayor a Menor)
    df_filtrado = df_full[df_full["categoria"] == categoria].copy()
    if "poblacion" in df_filtrado.columns:
        df_filtrado["poblacion"] = pd.to_numeric(df_filtrado["poblacion"], errors="coerce").fillna(0)
        df_filtrado = df_filtrado.sort_values(by="poblacion", ascending=False)
    
    if not df_filtrado.empty:
        # 1. Aseguramos que el índice sea limpio antes de editar
        df_filtrado = df_filtrado.reset_index(drop=True)

        # 2. Configuración de columnas
        column_config = {
            "id": None, 
            "nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
            "poblacion": st.column_config.NumberColumn("Pop.", format="%d", width="small", disabled=True, alignment="center"),
            "telefono": st.column_config.TextColumn("Teléfono", width="small", disabled=True, alignment="center"),
            "estado": st.column_config.SelectboxColumn("Estado", width="medium", options=OPCIONES_ESTADO, required=True, alignment="center"),
            "comentarios": st.column_config.TextColumn("Notas", width="medium", disabled=False, alignment="center"), 
        }
        
        # 3. EL TRUCO: Quitamos la capacidad de reordenar manualmente para que se quede fijo
        edited_df = st.data_editor(
            df_filtrado,
            column_order=["nombre", "poblacion", "telefono", "estado", "comentarios"], 
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="editor_leads"  # Esta clave debe ser fija
        )

        # Centramos el botón de sincronizar visualmente
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            boton = st.button("💾 Sincronizar Cambios", use_container_width=True)

        if boton:
            cambios_estado = edited_df["estado"] != df_filtrado["estado"]
            cambios_comentarios = edited_df["comentarios"] != df_filtrado.get("comentarios", pd.Series([""]*len(df_filtrado)))
            df_diff = edited_df[cambios_estado | cambios_comentarios]
            
            if not df_diff.empty:
                for _, row in df_diff.iterrows():
                    try:
                        conn.table("negocios").update({
                            "estado": str(row["estado"]),
                            "comentarios": str(row.get("comentarios", ""))
                        }).eq("id", int(row["id"])).execute()
                    except Exception as e:
                        st.error(f"Error en ID {row['id']}: {e}")
                
                st.success(f"✅ {len(df_diff)} registros actualizados.")
                st.cache_resource.clear() 
                st.rerun()
            else:
                st.info("No hay cambios detectados.")
    else:
        st.info(f"No hay registros para {categoria}")