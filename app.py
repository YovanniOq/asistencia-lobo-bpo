import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- CONEXIÓN DIRECTA ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- FUNCIÓN DE GRABACIÓN DIRECTA ---
def registrar_asistencia(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        # Creamos la fila exactamente como están tus encabezados en Drive
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), 
            "Nombre": nombre, 
            "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), 
            "Tipo": tipo, 
            "Observacion": obs, 
            "Tardanza_Min": 0
        }])
        
        # Leemos la hoja actual (Debe llamarse Sheet1 en tu Drive)
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        
        # Pegamos la nueva fila al final
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        
        # MANDAMOS A ESCRIBIR A DRIVE
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ REGISTRADO EN DRIVE: {tipo}")
        st.balloons()
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ ERROR DE PERMISOS: {e}")
        st.info("Asegúrate de compartir el Excel con el correo de la App como EDITOR.")

# --- INTERFAZ DE USUARIO ---
st.title("🐺 SR. LOBO BPO SOLUTIONS")
st.divider()

dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:")

if dni:
    # Cargamos empleados desde tu archivo local
    df_emp = pd.read_csv("empleados.csv")
    emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
    
    if not emp.empty:
        nombre = emp.iloc[0]['Nombre']
        st.info(f"👤 TRABAJADOR: {nombre}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📥 INGRESO", use_container_width=True):
                registrar_asistencia(dni, nombre, "INGRESO")
        with c2:
            # Botón de permiso simplificado para probar grabación
            if st.button("🚶 PERMISO", use_container_width=True):
                registrar_asistencia(dni, nombre, "PERMISO", obs="Salida rápida")
        with c3:
            if st.button("📤 SALIDA", use_container_width=True):
                registrar_asistencia(dni, nombre, "SALIDA")
    else:
        st.error("DNI no registrado.")
