import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
COSTO_MINUTO = 0.15  
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
    img { background-color: transparent !important; mix-blend-mode: multiply; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo):
    ahora = obtener_hora_peru()
    fecha_str = ahora.strftime("%Y-%m-%d")
    hora_str = ahora.strftime("%H:%M:%S")
    
    tardanza = 0
    if tipo == "INGRESO":
        h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
        if ahora.time() > h_oficial:
            diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
            tardanza = int(diff.total_seconds() / 60)

    nueva_fila = pd.DataFrame([{
        "Fecha": fecha_str, "DNI": str(dni), "Nombre": nombre,
        "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza
    }])
    
    df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
    st.success(f"✅ {tipo} REGISTRADO")
    time.sleep(2)
    st.session_state.reset_key += 1
    st.rerun()

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 4. INTERFAZ ---
modo = "Marcación"
with st.sidebar:
    st.image("Lobo.png", width=55) if os.path.exists("Lobo.png") else st.write("🐺 Gestión Lobo")
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026": modo = "Admin"

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # --- LÓGICA DE BLOQUEO ---
            df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            # Filtrar marcas de este trabajador hoy
            marcas_hoy = df_hist[(df_hist['DNI'] == str(dni_in)) & (df_hist['Fecha'] == hoy)]
            
            ya_ingreso = "INGRESO" in marcas_hoy['Tipo'].values
            ya_salio = "SALIDA" in marcas_hoy['Tipo'].values
            en_permiso = False
            if not marcas_hoy.empty:
                ultima_marca = marcas_hoy.iloc[-1]['Tipo']
                en_permiso = (ultima_marca == "SALIDA PERMISO")

            # --- BOTONES DINÁMICOS ---
            c1, c2 = st.columns(2)
            with c1:
                # Se deshabilita si ya ingresó hoy
                if st.button("📥 INGRESO", use_container_width=True, disabled=ya_ingreso):
                    registrar_en_nube(nombre, dni_in, "INGRESO")
            with c2:
                # Se deshabilita si no ha ingresado o si ya salió definitivamente
                if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_in, "SALIDA")
            
            c3, c4 = st.columns(2)
            with c3:
                # Solo si ya ingresó y no está ya en permiso o fuera
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_in, "SALIDA PERMISO")
            with c4:
                # Solo si salió de permiso
                if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_permiso)):
                    registrar_en_nube(nombre, dni_in, "ENTRADA PERMISO")
            
            if ya_salio: st.warning("Usted ya registró su salida definitiva por hoy.")
        else:
            st.error("DNI no registrado.")
else:
    st.header("📋 Reporte de Asistencia")
    st.dataframe(conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0))
