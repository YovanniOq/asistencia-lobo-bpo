import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ESTABLE ---
LOGO_ARCHIVO = "logo_lobo.png"
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. INTERFAZ Y FOCO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
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

# Menú Lateral (Sin cambios)
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])

# Encabezado (Diseño aprobado)
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 38px; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. FUNCIÓN DE GUARDADO (Corregida para evitar errores de callback) ---
def registrar_seguimiento(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Lectura forzada sin caché (ttl=0) para ver cambios inmediatos
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} guardado correctamente.")
        st.balloons()
        time.sleep(1)
        return True
    except Exception as e:
        if "200" in str(e) or "OK" in str(e):
            st.success(f"✅ {tipo} enviado a Drive.")
            st.balloons()
            time.sleep(1)
            return True
        else:
            st.error(f"Error: {e}")
            return False

# --- 5. LÓGICA DE MARCACIÓN ---
if modo == "Marcación":
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "pedir_obs" not in st.session_state: st.session_state.pedir_obs = False
    
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 3])
    with c_dni:
        dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        df_emp = pd.read_csv("empleados.csv")
        emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # Consulta fresca a la nube
            try:
                df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs_hoy = df_cloud[(df_cloud['DNI'].astype(str) == str(dni)) & (df_cloud['Fecha'] == hoy)]
                
                ya_ingreso = not marcs_hoy[marcs_hoy['Tipo'] == "INGRESO"].empty
                ultimo = marcs_hoy.iloc[-1]['Tipo'] if not marcs_hoy.empty else "NADA"
                ya_salio = not marcs_hoy[marcs_hoy['Tipo'] == "SALIDA"].empty
            except:
                ya_ingreso = False; ultimo = "NADA"; ya_salio = False

            if ya_salio:
                st.warning("🚫 Turno finalizado por hoy.")
            else:
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if st.button("📥 INGRESO", disabled=ya_ingreso, use_container_width=True):
                        if registrar_seguimiento(dni, nombre, "INGRESO"):
                            st.rerun()
                with b2:
                    if st.button("🚶 PERMISO", disabled=(not ya_ingreso or ultimo == "SALIDA_PERMISO"), use_container_width=True):
                        st.session_state.pedir_obs = True
                with b3:
                    if st.button("🔙 RETORNO", disabled=(ultimo != "SALIDA_PERMISO"), use_container_width=True):
                        if registrar_seguimiento(dni, nombre, "RETORNO_PERMISO"):
                            st.rerun()
                with b4:
                    if st.button("📤 SALIDA", disabled=(not ya_ingreso), use_container_width=True):
                        if registrar_seguimiento(dni, nombre, "SALIDA"):
                            st.rerun()

                if st.session_state.pedir_obs:
                    st.divider()
                    motive = st.text_input("MOTIVO DEL PERMISO (Escriba y ENTER):")
                    if motive:
                        if registrar_seguimiento(dni, nombre, "SALIDA_PERMISO", obs=motive):
                            st.session_state.pedir_obs = False
                            st.rerun()
        else:
            st.error("DNI no registrado.")
        
