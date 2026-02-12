import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco automático en la caja de DNI
components.html("<script>setInterval(function(){var inputs = window.parent.document.querySelectorAll('input'); if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') inputs[0].focus();}, 500);</script>", height=0)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False
if "ultimo_estado" not in st.session_state: st.session_state.ultimo_estado = {}

# --- 3. FUNCIÓN DE GRABACIÓN ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.session_state.ultimo_estado[str(dni)] = tipo
        st.success(f"✅ {tipo} REGISTRADO CORRECTAMENTE")
        st.balloons()
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        if "200" in str(e):
            st.session_state.ultimo_estado[str(dni)] = tipo
            st.session_state.reset_key += 1
            st.session_state.mostrar_obs = False
            st.rerun()
        else:
            st.error(f"Error de conexión: {e}")

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    st.title("🐺 Panel Admin")
    modo = "Marcación"
    if st.checkbox("Ver Reportes"):
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = "Historial"

# --- 5. LOGO Y DISEÑO ---
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"): 
        st.image("logo_lobo.png", width=150)
    else:
        st.write("🐺")
with col2:
    st.markdown("<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora Actual: {obtener_hora_peru().strftime('%H:%M:%S')}")

st.divider()

# --- 6. LÓGICA DE NEGOCIO ---
if modo == "Marcación":
    dni_in = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_{st.session_state.reset_key}")
    
    if dni_in:
        try:
            df_emp = pd.read_csv("empleados.csv")
            emp = df_emp[df_emp['DNI'].astype(str) == str(dni_in)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                estado = st.session_state.ultimo_estado.get(str(dni_in), "NADA")
                
                if estado == "SALIDA":
                    st.warning("🚫 Ya registraste tu salida definitiva por hoy.")
                else:
                    # CORRECCIÓN DE LA LÍNEA 88: Paréntesis cerrado correctamente
                    c1, c2, c3, c4 = st.columns(4)
                    
                    with c1:
                        if st.button("📥 INGRESO", disabled=(estado != "NADA"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "INGRESO")
                    
                    with c2:
                        if st.button("🚶 PERMISO", disabled=(estado != "INGRESO" and estado != "RETORNO_PERMISO"),
