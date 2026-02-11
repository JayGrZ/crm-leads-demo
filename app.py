import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# Configuración de página
st.set_page_config(page_title="CRM Lead Gen", page_icon="👥", layout="wide")

# --- CONEXIÓN ---
try:
    if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        s_url = st.secrets["connections"]["supabase"]["url"]
        s_key = st.secrets["connections"]["supabase"]["key"]
    else:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
    
    conn = st.connection("supabase", type=SupabaseConnection, url=s_url, key=s_key)
except Exception as e:
    st.error(f"Error crítico de conexión.")
    st.stop()

# --- Estilo Midnight ---
st.markdown(
    """
    <style>
    .stApp { background: #0E1117 !important; }
    [data-testid="stSidebar"] { background: #161B22 !important; }
    /* Centrado de cabeceras de tabla */
    [data-testid="stDataFrame"] th { text-align: center !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Funciones de Datos ---
def cargar_negocios():
    r = conn.table("negocios").select("*").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

CATEGORIAS = ["Bar", "Cafeterias", "Restaurantes"]
OPCIONES_ESTADO = ["🔴 Pendiente", "🟡 Llamando", "✅ Cita", "❌ No interesa"]

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
    
    # 1. FILTRADO Y ORDENACIÓN ESTRICTA
    df_filtrado = df_full[df_full["categoria"] == categoria].copy()
    
    if "poblacion" in df_filtrado.columns:
        df_filtrado["poblacion"] = pd.to_numeric(df_filtrado["poblacion"], errors="coerce").fillna(0)
        # Ordenamos y RESETEAMOS el índice para que sea fijo (0, 1, 2...)
        df_filtrado = df_filtrado.sort_values(by="poblacion", ascending=False).reset_index(drop=True)
    
    if not df_filtrado.empty:
        # 2. CONFIGURACIÓN CON CENTRADO (alignment="center")
        column_config = {
            "id": None, 
            "nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
            "poblacion": st.column_config.NumberColumn("Pop.", format="%d", width="small", disabled=True, alignment="center"),
            "telefono": st.column_config.TextColumn("Teléfono", width="small", disabled=True, alignment="center"),
            "estado": st.column_config.SelectboxColumn("Estado", width="medium", options=OPCIONES_ESTADO, required=True, alignment="center"),
            "comentarios": st.column_config.TextColumn("Notas", width="medium", disabled=False, alignment="center"), 
        }
        
        # 3. EL EDITOR (usamos el DataFrame con el índice reseteado)
        edited_df = st.data_editor(
            df_filtrado,
            column_order=["nombre", "poblacion", "telefono", "estado", "comentarios"], 
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key=f"editor_{categoria}" # Key dinámica por categoría para evitar conflictos
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("💾 Sincronizar Cambios", use_container_width=True):
                # Comparamos contra df_filtrado (que tiene el mismo índice)
                cambios_mask = (edited_df["estado"] != df_filtrado["estado"]) | \
                               (edited_df["comentarios"].fillna("") != df_filtrado["comentarios"].fillna(""))
                
                df_diff = edited_df[cambios_mask]
                
                if not df_diff.empty:
                    for _, row in df_diff.iterrows():
                        try:
                            conn.table("negocios").update({
                                "estado": str(row["estado"]),
                                "comentarios": str(row["comentarios"]) if pd.notna(row["comentarios"]) else ""
                            }).eq("id", int(row["id"])).execute()
                        except Exception as e:
                            st.error(f"Error al guardar ID {row['id']}: {e}")
                    
                    st.success(f"✅ {len(df_diff)} registros actualizados.")
                    st.cache_resource.clear() 
                    st.rerun()
                else:
                    st.info("No se detectaron cambios.")
    else:
        st.info(f"No hay registros para {categoria}")