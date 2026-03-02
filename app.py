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
        position: relative;
    }
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo):
    try:
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
            "Fecha": fecha_str, "DNI": str(dni).strip(), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza
        }])
        
        # FORZAMOS LECTURA FRESCA PARA COMPARAR
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 4. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    if os.path.exists("Lobo.png"): st.image("Lobo.png", width=55)
    st.markdown("<h2 style='color: #1E3A8A; font-size: 21px; margin: 0;'>Gestión Lobo</h2>", unsafe_allow_html=True)
    
    st.divider()
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# --- FOCO INTELIGENTE ---
if not acceso_admin:
    components.html("""<script>
        const f = () => {
            const i = window.parent.document.querySelectorAll('input[type="text"]');
            if (i.length > 0 && window.parent.document.activeElement !== i[0]) i[0].focus();
        };
        setInterval(f, 1000);
    </script>""", height=0)

# --- 5. CABECERA PRINCIPAL ---
c_izq, c_logo_p, c_tit, c_der = st.columns([0.5, 3.5, 6, 0.5])
with c_logo_p:
    if os.path.exists("logo_lobo.png"):
        st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
        st.image("logo_lobo.png", width=320)
        st.markdown("</div>", unsafe_allow_html=True)
with c_tit:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 50px;'>Marcación Sr. Lobo</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        dni_limpio = str(dni_in).strip()
        emp = df_emp[df_emp['DNI'] == dni_limpio]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # --- LÓGICA DE BLOQUEO REAL ---
            # Leemos la nube asegurando que DNI sea texto para comparar bien
            df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            df_hist['DNI'] = df_hist['DNI'].astype(str).str.strip()
            
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            marcas_hoy = df_hist[(df_hist['DNI'] == dni_limpio) & (df_hist['Fecha'] == hoy)]
            
            # Estados de marcación
            ya_ingreso = "INGRESO" in marcas_hoy['Tipo'].values
            ya_salio = "SALIDA" in marcas_hoy['Tipo'].values
            en_permiso = (not marcas_hoy.empty and marcas_hoy.iloc[-1]['Tipo'] == "SALIDA PERMISO")

            # --- RENDERIZADO DE BOTONES ---
            c1, c2 = st.columns(2)
            with c1:
                # Se BLOQUEA si ya hay un ingreso hoy
                if st.button("📥 INGRESO", use_container_width=True, disabled=ya_ingreso):
                    registrar_en_nube(nombre, dni_limpio, "INGRESO")
            with c2:
                # Se HABILITA solo si ya entró y no ha salido definitivamente
                if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_limpio, "SALIDA")
            
            c3, c4 = st.columns(2)
            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_limpio, "SALIDA PERMISO")
            with c4:
                if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_permiso)):
                    registrar_en_nube(nombre, dni_limpio, "ENTRADA PERMISO")
            
            if ya_salio: st.warning("Usted ya registró su salida definitiva hoy.")
        else:
            st.error("DNI no registrado.")
else:
    st.header("📋 Reporte Auditado")
    st.dataframe(conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0), use_container_width=True)
