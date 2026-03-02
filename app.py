import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time 
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MENSUAL = 30 

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover; background-attachment: fixed;
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.94);
        padding: 3rem; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.1);
    }
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo, salario, obs=""):
    try:
        ahora = obtener_hora_peru()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        
        tardanza_hoy = 0
        descuento_hoy = 0
        if tipo == "INGRESO":
            h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if ahora.time() > h_oficial:
                diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
                tardanza_hoy = int(diff.total_seconds() / 60)
                # Cálculo proporcional al salario
                descuento_hoy = round(tardanza_hoy * (salario / 30 / 8 / 60), 2)

        nueva_fila = pd.DataFrame([{
            "Fecha": fecha_str, "DNI": str(dni).strip(), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza_hoy,
            "Descuento_Soles": descuento_hoy, "Observacion": obs
        }])
        
        df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_hist, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.5)
        # Limpieza de estados al terminar
        if "p_m" in st.session_state: st.session_state.p_m = False
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. CONEXIÓN Y FOCO ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

components.html("""
    <script>
    const f = () => {
        const i = window.parent.document.querySelectorAll('input[type="text"]');
        if (i.length > 0) {
            const active = window.parent.document.activeElement;
            if (active.tagName !== 'INPUT' && active.tagName !== 'TEXTAREA') { i[0].focus(); }
        }
    };
    setInterval(f, 2000);
    </script>
""", height=0)

# --- 4. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    if os.path.exists("Lobo.png"): st.image("Lobo.png", width=55)
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026": modo = "Admin"

# --- 5. CABECERA ---
c_logo, c_tit = st.columns([1, 2.5])
with c_logo:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=300)
with c_tit:
    st.markdown("<h1 style='color: #1E3A8A;'>Marcación Sr. Lobo</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni_box, _ = st.columns([0.15, 0.85]) 
    with c_dni_box:
        dni_in = st.text_input("DNI", key=f"dni_{st.
