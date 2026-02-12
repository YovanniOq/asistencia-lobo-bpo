import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
LOGO_ARCHIVO = "logo_lobo.png"
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# --- 3. CONEXIÓN ---
# Forzamos la conexión a que no use memoria caché
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. FUNCIÓN DE GUARDADO (RECONSTRUIDA) ---
def registrar_dato(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Leemos el estado actual de la hoja (Sheet1)
        # Si esto falla, el problema es el nombre de la pestaña en Drive
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        
        # Unimos lo viejo con lo nuevo
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        
        # ACTUALIZACIÓN CRÍTICA
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ REGISTRO CONFIRMADO EN DRIVE")
        st.balloons()
        time.sleep(2)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
        
    except Exception as e:
        # Si sale el error 200, intentamos confirmar si se grabó
        if "200" in str(e):
            st.warning("⚠️ Google respondió lento, verificando grabación...")
            time.sleep(2)
            st.rerun()
        else:
            st.error(f"❌ ERROR REAL DE CONEXIÓN: {e}")
            st.info("Revisa que la pestaña en tu Drive se llame exactamente 'Sheet1'")

# --- 5. LÓGICA DE LA APP (IGUAL A LA ANTERIOR) ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False

col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO): st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

st.write("### DIGITE SU DNI:")
dni_input = st.text_input("", key=f"in_{st.session_state.reset_key}", label_visibility="collapsed")

if dni_input:
    df_emp = pd.read_csv("empleados.csv")
    emp = df_emp[df_emp['DNI'].astype(str) == str(dni_input)]
    
    if not emp.empty:
        nombre = emp.iloc[0]['Nombre']
        st.info(f"👤 TRABAJADOR: {nombre}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("📥 INGRESO", use_container_width=True):
                registrar_dato(dni_input, nombre, "INGRESO")
        with col2:
            if st.button("🚶 PERMISO", use_container_width=True):
                st.session_state.mostrar_obs = True
                st.rerun()
        with col3:
            if st.button("🔙 RETORNO", use_container_width=True):
                registrar_dato(dni_input, nombre, "RETORNO_PERMISO")
        with col4:
            if st.button("📤 SALIDA", use_container_width=True):
                registrar_dato(dni_input, nombre, "SALIDA")

        if st.session_state.mostrar_obs:
            motivo = st.text_input("MOTIVO DEL PERMISO:")
            if motivo: registrar_dato(dni_input, nombre, "SALIDA_PERMISO", obs=motivo)
    else:
        st.error("DNI no registrado.")
