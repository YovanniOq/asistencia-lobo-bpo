import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time

# --- 1. CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00"
TOLERANCIA_MIN = 30
LOGO_ARCHIVO = "logo_lobo.png"

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Asistencia Sr. Lobo", layout="wide")

# CSS para el diseño compacto que pediste
st.markdown("""
    <style>
    .stTextInput { width: 250px !important; }
    .main-title { font-size: 35px !important; font-weight: bold; color: #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

# Encabezado: Logo y Título
col_l, col_t = st.columns([1, 4])
with col_l:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_t:
    st.markdown('<p class="main-title">SR. LOBO BPO SOLUTIONS SAC</p>', unsafe_allow_html=True)

st.divider()

# --- 3. CONEXIÓN ROBUSTA ---
try:
    # Forzamos la limpieza de la llave privada del JSON
    secrets_dict = st.secrets["connections"]["gsheets"].to_dict()
    if "\\n" in secrets_dict["private_key"]:
        secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error técnico en la llave JSON: {e}")

# --- 4. LÓGICA DE MARCACIÓN ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

st.subheader("DIGITE SU DNI Y PRESIONE ENTER:")
# Caja de DNI chica como pediste
dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

if dni:
    try:
        # Cargamos empleados locales
        df_empleados = pd.read_csv("empleados.csv")
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.success(f"👤 TRABAJADOR: {nombre}")
            
            # LEER NUBE (Aquí es donde daba el error)
            # Usamos ttl=0 para que no use memoria vieja y vea tus títulos nuevos
            df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            
            # BOTONES
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("📥 INGRESO", use_container_width=True):
                    # Lógica de guardado...
                    st.info("Guardando en la nube...")
                    # (Aquí iría la función de registrar_en_nube que ya tenemos)
        else:
            st.error("DNI no registrado en empleados.csv")
    except Exception as e:
        st.error(f"Error de acceso: El sistema no reconoce las columnas. Verifica que en Sheet1 diga exactamente: DNI, Nombre, Fecha, Hora, Tipo, Observacion, Tardanza_Min")
        st.info("💡 Consejo: Asegúrate de que no haya filas vacías arriba de los títulos en Google Sheets.")
