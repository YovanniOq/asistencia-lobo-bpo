import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco automático en la caja de DNI
components.html("<script>setInterval(function(){var inputs = window.parent.document.querySelectorAll('input'); if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') inputs[0].focus();}, 500);</script>", height=0)

# --- 2. CONEXIÓN DIRECTA ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# Estados de sesión (Memoria de la App)
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "ultimo_estado" not in st.session_state: st.session_state.ultimo_estado = {}

# --- 3. EL MOTOR DE GRABACIÓN ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Leemos y actualizamos Sheet1 (Asegúrate que se llame así en tu Drive)
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        # Guardamos en la memoria local para que los botones cambien al instante
        st.session_state.ultimo_estado[str(dni)] = tipo
        st.success(f"✅ {tipo} REGISTRADO")
        st.balloons()
        time.sleep(1.5)
        st.session_state.reset_key += 1 # Limpia la caja de DNI
        st.rerun()
    except Exception as e:
        if "200" in str(e): # Bypass para el error de respuesta de Google
            st.session_state.ultimo_estado[str(dni)] = tipo
            st.session_state.reset_key += 1
            st.rerun()
        else:
            st.error(f"❌ Error de permisos: {e}. Verifica que el Excel esté compartido como EDITOR.")

# --- 4. MENÚ LATERAL Y LOGO ---
with st.sidebar:
    st.title("🐺 Panel Admin")
    modo = "Marcación"
    if st.checkbox("Ver Reportes"):
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = "Historial"

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=150)
with col2:
    st.markdown(f"<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora: {obtener_hora_peru().strftime('%H:%M:%S')}")

st.divider()

# --- 5. LÓGICA DE TRABAJO ---
if modo == "Marcación":
    dni_in = st.text_input("DIGITE SU DNI:", key=f"dni_{st.session_state.reset_key}")
    
    if dni_in:
        try:
            df_emp = pd.read_csv("empleados.csv")
            emp = df_emp[df_emp['DNI'].astype(str) == str(dni_in)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                # Obtenemos el último movimiento de hoy
                estado = st.session_state.ultimo_estado.get(str(dni_in), "NADA")
                
                if estado == "SALIDA":
                    st.warning("🚫 Ya marcaste tu salida final.")
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: # Botón INGRESO
                        if st.button("📥 INGRESO", disabled=(estado != "NADA"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "INGRESO")
                    with c2: # Botón PERMISO
                        if st.button("🚶 PERMISO", disabled=(estado != "INGRESO" and estado != "RETORNO_PERMISO"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs="En permiso")
                    with c3: # Botón RETORNO
                        if st.button("🔙 RETORNO", disabled=(estado != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
                    with col4: # Botón SALIDA
                        if st.button("📤 SALIDA", disabled=(estado == "NADA"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "SALIDA")
            else:
                st.error("DNI no encontrado.")
        except Exception as e:
            st.error("Cargando base de datos...")

else: # MODO HISTORIAL
    st.header("📋 Reporte en Drive")
    try:
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        st.dataframe(df_h, use_container_width=True)
    except:
        st.error("No se pudo cargar la tabla. Revisa Sheet1.")
