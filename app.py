import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00"
TOLERANCIA_MIN = 30
LOGO_ARCHIVO = "logo_lobo.png"

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. INTERFAZ Y FOCO AUTOMÁTICO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# SCRIPT DE FOCO: Esto obliga al cursor a estar en el DNI siempre
components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') {
            inputs[0].focus();
        }
    }
    setInterval(setFocus, 500);
    </script>
""", height=0)

# Diseño: Logo y Título sin SAC
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 38px; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- 4. MARCACIÓN ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

st.write("### DIGITE SU DNI Y PRESIONE ENTER:")

# CAJA CHICA: Solo ocupa 250px de ancho
c_dni, c_espacio = st.columns([1, 3])
with c_dni:
    dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

if dni:
    try:
        df_emp = pd.read_csv("empleados.csv")
        emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.success(f"👤 TRABAJADOR: {nombre}")
            
            # Botones de marcación
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("📥 INGRESO", use_container_width=True):
                    guardar(dni, nombre, "INGRESO", url_hoja, conn)
            with col2:
                if st.button("🚶 PERMISO", use_container_width=True):
                    guardar(dni, nombre, "SALIDA_PERMISO", url_hoja, conn)
            with col3:
                if st.button("🔙 RETORNO", use_container_width=True):
                    guardar(dni, nombre, "RETORNO_PERMISO", url_hoja, conn)
            with col4:
                if st.button("📤 SALIDA", use_container_width=True):
                    guardar(dni, nombre, "SALIDA", url_hoja, conn)
        else:
            st.error("DNI no registrado.")
            time.sleep(1)
            st.session_state.reset_key += 1
            st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

def guardar(dni, nombre, tipo, url, con_obj):
    try:
        ahora = obtener_hora_peru()
        nueva = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": "", "Tardanza_Min": 0
        }])
        # Leemos y concatenamos
        df_actual = con_obj.read(spreadsheet=url, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva], ignore_index=True)
        con_obj.update(spreadsheet=url, worksheet="Sheet1", data=df_final)
        
        st.balloons()
        st.success("✅ Registrado con éxito.")
        time.sleep(2)
        st.session_state.reset_key += 1
        st.rerun()
    except:
        st.error("Error al guardar en Drive. Verifica que la pestaña se llame Sheet1.")
