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

# --- ESTILOS CSS: FONDO, MARCA DE AGUA Y ALINEACIÓN HORIZONTAL ---
st.markdown("""
    <style>
    /* Fondo de oficina general */
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Contenedor principal con MARCA DE AGUA sutil */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 3rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        position: relative;
    }

    /* Gota de agua del Lobo centrada en el fondo del reporte */
    .main .block-container::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 500px;
        height: 500px;
        background-image: url("https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        opacity: 0.04; 
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 0;
    }

    /* BLOQUE ÚNICO PARA ALINEACIÓN HORIZONTAL PERFECTA */
    .sidebar-brand-horizontal {
        display: flex;
        flex-direction: row;
        align-items: center; /* Centrado vertical entre logo y texto */
        justify-content: flex-start;
        gap: 12px;
        margin-bottom: 25px;
        padding: 10px 0;
    }
    .sidebar-brand-horizontal img {
        width: 35px; /* Tamaño homogéneo */
        height: 35px;
        object-fit: contain;
    }
    .sidebar-brand-horizontal span {
        color: #1E3A8A;
        font-size: 22px;
        font-weight: bold;
        font-family: sans-serif;
        white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- JAVASCRIPT DE FOCO INTELIGENTE ---
components.html("""
    <script>
    const forceFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        const passInputs = window.parent.document.querySelectorAll('input[type="password"]');
        if (inputs.length > 0) {
            const dniInput = inputs[0];
            const activeElem = window.parent.document.activeElement;
            let escribiendoPass = false;
            passInputs.forEach(p => { if(activeElem === p) escribiendoPass = true; });
            if (activeElem !== dniInput && !escribiendoPass) {
                dniInput.focus();
            }
        }
    };
    setInterval(forceFocus, 1000);
    </script>
""", height=0)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 3. LÓGICA DE REGISTRO ---
def registrar_en_nube(dni, nombre, tipo):
    try:
        ahora = obtener_hora_peru()
        tardanza_min = 0
        if tipo == "INGRESO":
            hora_act = ahora.time()
            hora_lim = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if hora_act > hora_lim:
                diff = datetime.combine(datetime.today(), hora_act) - datetime.combine(datetime.today(), hora_lim)
                tardanza_min = int(diff.total_seconds() / 60)

        nueva_fila = pd.DataFrame([{
            "DNI": str(dni).strip(), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Tardanza_Min": tardanza_min
        }])
        
        st.cache_data.clear()
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_h, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.2); st.session_state.reset_key += 1; st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- 4. INTERFAZ ---
modo = "Marcación"
with st.sidebar:
    # --- CABECERA HORIZONTAL: LOBO A LA IZQUIERDA DEL TEXTO ---
    # Usamos HTML directo para forzar la posición horizontal exacta
    st.markdown(f"""
        <div class="sidebar-brand-horizontal">
            <img src="https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png">
            <span>Gestión Lobo</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# Cabecera principal (RESTAURADA A 50PX Y CENTRADA)
c_izq, c_logo, c_tit, c_der = st.columns([1, 3, 6, 1])
with c_logo:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=300)
with c_tit:
    st.markdown(f"""
        <div style='padding-top: 15px;'>
            <h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>Marcación Sr. Lobo</h1>
            <h3 style='color: #444; font-size: 26px; margin-top: -10px;'>Sr. Lobo BPO Solutions</h3>
        </div>
    """, unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 4])
    with c_dni:
        # SE MANTIENE EL LÍMITE DE 12 CARACTERES
        dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        st.cache_data.clear()
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            c_btns = st.columns(2)
            with c_btns[0]:
                if st.button("📥 INGRESO", use_container_width=True): registrar_en_nube(dni_in, nombre, "INGRESO")
            with c_btns[1]:
                if st.button("📤 SALIDA", use_container_width=True): registrar_en_nube(dni_in, nombre, "SALIDA")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN CON MARCA DE AGUA ---
    st.header("📋 Reporte Auditado de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        resumen = df_h.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento'] = resumen['Excedente'] * COSTO_MINUTO

        st.dataframe(df_h.drop(columns=['Fecha_dt']), use_container_width=True)
        st.subheader("💰 Resumen de Auditoría")
        st.table(resumen)
        st.metric("Total General a Descontar", f"S/ {resumen['Descuento'].sum():.2f}")
