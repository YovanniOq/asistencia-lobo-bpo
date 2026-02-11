import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time

# --- 1. CONFIGURACIÓN Y LIMPIEZA DE LLAVE ---
def preparar_conexion():
    try:
        # Extraemos la configuración de los secrets
        conf = st.secrets["connections"]["gsheets"].to_dict()
        
        # Reparamos los saltos de línea en la llave privada si vienen como texto "\n"
        if "\\n" in conf["private_key"]:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n")
        
        return conf
    except Exception as e:
        st.error(f"Error al leer Secrets: {e}")
        return None

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. LÓGICA DE AUTO-REPARACIÓN ---
def asegurar_encabezados(conn, spreadsheet_id):
    try:
        # Intentamos leer la hoja
        df = conn.read(spreadsheet=spreadsheet_id, worksheet="Sheet1", ttl=0)
        
        # Si la hoja está totalmente vacía o no tiene columnas
        if df.empty or len(df.columns) < 2:
            st.info("Configurando encabezados automáticamente en Sheet1...")
            encabezados = pd.DataFrame(columns=["DNI", "Nombre", "Fecha", "Hora", "Tipo", "Observacion", "Tardanza_Min"])
            conn.update(spreadsheet=spreadsheet_id, worksheet="Sheet1", data=encabezados)
            return True
        return True
    except Exception as e:
        st.warning(f"Aviso de conexión: {e}")
        return False

# --- INTERFAZ ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# Inicializar conexión
config_lista = preparar_conexion()
conn = st.connection("gsheets", type=GSheetsConnection)
id_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# Título y Diseño
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"):
        st.image("logo_lobo.png", width=180)
with col2:
    st.markdown("<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)

st.divider()

# Ejecutar auto-reparación
if asegurar_encabezados(conn, id_hoja):
    st.success("✅ Sistema conectado a la nube y listo.")
else:
    st.error("❌ No se pudo validar la hoja. Verifica permisos de Editor.")

# Caja de DNI compacta
c_dni, c_vacio = st.columns([1, 3])
with c_dni:
    dni_input = st.text_input("DIGITE SU DNI:", key="dni_input")

if dni_input:
    st.write(f"Procesando DNI: {dni_input}...")
    # Aquí continuaremos con la lógica de botones que elegiste (Opción 2)
