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

# --- ESTILOS CSS: LOGOS TRANSPARENTES Y AJUSTE DE ALTURA ---
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
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        
        tardanza = 0
        descuento = 0
        if tipo == "INGRESO":
            h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if ahora.time() > h_oficial:
                diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
                tardanza = int(diff.total_seconds() / 60)
                descuento = round(tardanza * COSTO_MINUTO, 2)

        nueva_fila = pd.DataFrame([{
            "Fecha": fecha_str, "DNI": str(dni).strip(), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza,
            "Descuento_Soles": descuento, "Observacion": obs
        }])
        
        df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_hist, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO CORRECTAMENTE")
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 4. CABECERA PRINCIPAL ---
c_logo, c_tit = st.columns([1, 2.5])
with c_logo:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=320) #
with c_tit:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 50px; margin-top: 10px;'>Marcación Sr. Lobo</h1>", unsafe_allow_html=True)

st.divider()

# --- 5. INTERFAZ DE MARCACIÓN ---
st.write("### DIGITE SU DNI:")
# COLUMNA MINI PARA EL DNI (Ajuste a 12 caracteres visualmente)
c_dni_fix, _ = st.columns([0.15, 0.85]) 
with c_dni_fix:
    dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12) #

if dni_in:
    df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
    dni_limpio = str(dni_in).strip()
    emp = df_emp[df_emp['DNI'] == dni_limpio]
    
    if not emp.empty:
        nombre = emp.iloc[0]['Nombre']
        st.info(f"👤 TRABAJADOR: {nombre}") #
        
        # --- LÓGICA DE BLOQUEO ESTRICTA ---
        df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_hist['DNI'] = df_hist['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        hoy = obtener_hora_peru().strftime("%Y-%m-%d")
        marcas_hoy = df_hist[(df_hist['DNI'] == dni_limpio) & (df_hist['Fecha'] == hoy)]
        
        ya_ingreso = "INGRESO" in marcas_hoy['Tipo'].values
        ya_salio = "SALIDA" in marcas_hoy['Tipo'].values
        en_permiso = (not marcas_hoy.empty and marcas_hoy.iloc[-1]['Tipo'] == "SALIDA PERMISO")

        # CAMPO DE OBSERVACIÓN PARA PERMISOS
        obs_txt = ""
        if ya_ingreso and not ya_salio:
            obs_txt = st.text_area("Motivo / Observación:", height=70)

        # RENDER DE BOTONES CON BLOQUEO REAL
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 INGRESO", use_container_width=True, disabled=ya_ingreso):
                registrar_en_nube(nombre, dni_limpio, "INGRESO")
        with c2:
            if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                registrar_en_nube(nombre, dni_limpio, "SALIDA", obs_txt)
        
        c3, c4 = st.columns(2)
        with c3:
            if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                registrar_en_nube(nombre, dni_limpio, "SALIDA PERMISO", obs_txt)
        with c4:
            if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_permiso)):
                registrar_en_nube(nombre, dni_limpio, "ENTRADA PERMISO", obs_txt)
        
        if ya_salio: st.warning("Usted ya registró su salida definitiva hoy.")
    else:
        st.error("DNI no registrado.")
