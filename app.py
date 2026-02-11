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

# --- 2. INTERFAZ Y FOCO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# Script para mantener el cursor siempre listo en el DNI
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

# Menú Lateral para Administrador
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])
        elif clave != "":
            st.error("Clave incorrecta")

# Encabezado sin SAC
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 38px; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora actual: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("Fallo de conexión. Verifica tus Secrets.")

# --- 4. FUNCIÓN DE GUARDADO (Captura el Response 200 como Éxito) ---
def registrar(dni, nombre, tipo):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": "", "Tardanza_Min": 0
        }])
        
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        
        # Intentamos actualizar
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.balloons()
        st.success(f"✅ {tipo} registrado correctamente.")
        time.sleep(2)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        # Si Google responde 200, es que sí guardó aunque la librería de error
        if "200" in str(e):
            st.balloons()
            st.success(f"✅ {tipo} guardado en Drive.")
            time.sleep(2)
            st.session_state.reset_key += 1
            st.rerun()
        else:
            st.error(f"Error al guardar: {e}")

# --- 5. LÓGICA DE PANTALLA ---
if modo == "Marcación":
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    
    st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
    c_dni, _ = st.columns([1, 3])
    with c_dni:
        dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        try:
            df_emp = pd.read_csv("empleados.csv")
            emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.success(f"👤 TRABAJADOR: {nombre}")
                
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if st.button("📥 INGRESO", use_container_width=True):
                        registrar(dni, nombre, "INGRESO")
                with b2:
                    if st.button("🚶 PERMISO", use_container_width=True):
                        registrar(dni, nombre, "SALIDA_PERMISO")
                with b3:
                    if st.button("🔙 RETORNO", use_container_width=True):
                        registrar(dni, nombre, "RETORNO_PERMISO")
                with b4:
                    if st.button("📤 SALIDA", use_container_width=True):
                        registrar(dni, nombre, "SALIDA")
            else:
                st.error("DNI no registrado.")
                time.sleep(1)
                st.session_state.reset_key += 1
                st.rerun()
        except Exception as e:
            st.error(f"Error de lectura local: {e}")

elif modo == "Historial Mensual":
    st.header("📋 Reporte de Asistencias en Drive")
    try:
        df_nube = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        st.dataframe(df_nube, use_container_width=True)
    except:
        st.error("No se pudo cargar el historial desde la nube.")
