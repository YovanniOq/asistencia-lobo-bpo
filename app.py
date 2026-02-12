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

# --- 2. INTERFAZ Y FOCO AUTOMÁTICO ---
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

# Menú Lateral
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])

# Encabezado
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 38px; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. FUNCIÓN DE GUARDADO (IGNORA EL FALSO ERROR) ---
def registrar_seguimiento(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Leemos el estado actual
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        
        # Intentamos subir
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.balloons()
        st.success(f"✅ {tipo} registrado.")
        time.sleep(2)
        st.session_state.reset_key += 1
        st.session_state.esperando_motivo = False
        st.rerun()

    except Exception as e:
        # SI EL ERROR CONTIENE 200, ES UN ÉXITO DISFRAZADO
        if "200" in str(e) or "OK" in str(e):
            st.balloons()
            st.success(f"✅ {tipo} registrado exitosamente.")
            time.sleep(2)
            st.session_state.reset_key += 1
            st.session_state.esperando_motivo = False
            st.rerun()
        else:
            st.error(f"Fallo real: {e}")

# --- 5. LÓGICA DE MARCACIÓN ---
if modo == "Marcación":
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "esperando_motivo" not in st.session_state: st.session_state.esperando_motivo = False
    
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 3])
    with c_dni:
        dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        try:
            df_emp = pd.read_csv("empleados.csv")
            emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                # Bloque de lectura para flujo de botones (con captura de error 200)
                try:
                    df_nube = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                except Exception as e:
                    if "200" in str(e):
                        # Si da error 200 al leer, usamos un DF vacío para no trabar el sistema
                        df_nube = pd.DataFrame(columns=["DNI", "Fecha", "Tipo"])
                    else:
                        st.error("Error al conectar con la nube.")
                        st.stop()

                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs_hoy = df_nube[(df_nube['DNI'].astype(str) == str(dni)) & (df_nube['Fecha'] == hoy)]
                ultimo = marcs_hoy.iloc[-1]['Tipo'] if not marcs_hoy.empty else "NADA"

                if ultimo == "SALIDA":
                    st.warning("🚫 Turno completado por hoy.")
                else:
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        if st.button("📥 INGRESO", disabled=(ultimo != "NADA"), use_container_width=True):
                            registrar_seguimiento(dni, nombre, "INGRESO")
                    with b2:
                        if st.button("🚶 PERMISO", disabled=(ultimo not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            st.session_state.esperando_motivo = True
                    with b3:
                        if st.button("🔙 RETORNO", disabled=(ultimo != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_seguimiento(dni, nombre, "RETORNO_PERMISO")
                    with b4:
                        if st.button("📤 SALIDA", disabled=(ultimo not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            registrar_seguimiento(dni, nombre, "SALIDA")

                    if st.session_state.esperando_motivo:
                        st.divider()
                        motivo = st.text_input("MOTIVO DEL PERMISO (Escriba y presione ENTER):")
                        if motivo:
                            registrar_seguimiento(dni, nombre, "SALIDA_PERMISO", obs=motivo)
            else:
                st.error("DNI no registrado.")
        except Exception as e:
            st.error(f"Error técnico: {e}")

elif modo == "Historial Mensual":
    st.header("📋 Historial")
    df_nube = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    st.dataframe(df_nube, use_container_width=True)
