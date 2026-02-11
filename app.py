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

# Título sin SAC y Caja de DNI chica
col_l, col_t = st.columns([1, 4])
with col_l:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=180)
with col_t:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 40px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora actual: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error de conexión inicial: {e}")

# --- 4. MARCACIÓN ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
c_dni, c_vacio = st.columns([1, 3])
with c_dni:
    dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

if dni:
    try:
        # Carga de empleados local
        df_emp = pd.read_csv("empleados.csv")
        emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.success(f"👤 TRABAJADOR: {nombre}")
            
            # Intentar leer la nube de forma ultra-flexible
            try:
                # Leemos TODO sin validar columnas primero para evitar el error rojo
                df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                
                # BOTONES (Sin filtros para que no falle)
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("📥 INGRESO", use_container_width=True):
                        registrar_asistencia(dni, nombre, "INGRESO", url_hoja, conn)
                with c2:
                    if st.button("🚶 PERMISO", use_container_width=True):
                        registrar_asistencia(dni, nombre, "SALIDA_PERMISO", url_hoja, conn)
                with c3:
                    if st.button("🔙 RETORNO", use_container_width=True):
                        registrar_asistencia(dni, nombre, "RETORNO_PERMISO", url_hoja, conn)
                with c4:
                    if st.button("📤 SALIDA", use_container_width=True):
                        registrar_asistencia(dni, nombre, "SALIDA", url_hoja, conn)
            except:
                st.error("Error al conectar con la pestaña Sheet1. Revisa que el nombre sea exacto.")
        else:
            st.error("DNI no registrado.")
    except Exception as e:
        st.error(f"Error crítico: {e}")

def registrar_asistencia(dni, nombre, tipo, url, con_obj):
    try:
        ahora = obtener_hora_peru()
        # Creamos la fila nueva
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), 
            "Nombre": nombre, 
            "Fecha": ahora.strftime("%Y-%m-%d"), 
            "Hora": ahora.strftime("%H:%M:%S"), 
            "Tipo": tipo,
            "Observacion": "",
            "Tardanza_Min": 0
        }])
        
        # Leemos lo actual
        df_actual = con_obj.read(spreadsheet=url, worksheet="Sheet1", ttl=0)
        # Unimos
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        # Subimos
        con_obj.update(spreadsheet=url, worksheet="Sheet1", data=df_final)
        
        st.balloons()
        st.success(f"✅ {tipo} registrado en Google Drive")
        time.sleep(2)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"No se pudo guardar en la nube: {e}")
