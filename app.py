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

# --- ESTILOS CSS: FONDO PROFESIONAL SIN CAJAS BLANCAS ---
st.markdown("""
    <style>
    /* Fondo de oficina profesional */
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Contenedor principal con MARCA DE AGUA sutil (Gota de agua) */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 3rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        position: relative;
        overflow: hidden;
    }

    /* Gota de agua sutil en el reporte */
    .main .block-container::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 500px;
        height: 500px;
        /* IMPORTANTE: Usar versión con fondo transparente */
        background-image: url("https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        opacity: 0.04; 
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 0;
    }

    /* Alineación de Sidebar */
    .sidebar-brand-horizontal {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 12px;
        margin-bottom: 25px;
        padding-top: 10px;
    }
    
    /* Elimina bordes o fondos si Streamlit intenta ponerlos */
    .stImage > img {
        background-color: transparent !important;
        border: none !important;
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
        if (inputs.length > 0) {
            const dniInput = inputs[0];
            if (window.parent.document.activeElement !== dniInput) {
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

# --- 3. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    # --- CABECERA LATERAL: LOBO PEQUEÑO AL COSTADO IZQUIERDO (CON FONDO TRANSPARENTE) ---
    st.markdown(f"""
        <div class="sidebar-brand-horizontal">
            <img src="https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png" style="width: 35px; height: auto;">
            <h2 style='color: #1E3A8A; font-size: 22px; margin: 0;'>Gestión Lobo</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# --- 4. CABECERA PRINCIPAL (CON LOGO CENTRAL TRANSPARENTE) ---
c_izq, c_logo_p, c_tit, c_der = st.columns([1, 3.5, 6, 1])
with c_logo_p:
    # IMPORTANTE: Esta URL debe ser un PNG transparente
    st.markdown("<div style='padding-top: 40px;'>", unsafe_allow_html=True)
    st.image("https://raw.githubusercontent.com/Yovanni/asistencia/main/logo_lobo.png", width=320)
    st.markdown("</div>", unsafe_allow_html=True)
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
        # Lógica de marcación...
        st.cache_data.clear()
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            c_btns = st.columns(2)
            with c_btns[0]:
                if st.button("📥 INGRESO", use_container_width=True): st.success("INGRESO")
            with c_btns[1]:
                if st.button("📤 SALIDA", use_container_width=True): st.success("SALIDA")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN CON MARCA DE AGUA Y AUDITORÍA ---
    st.header("📋 Reporte Auditado de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        # ... (Cálculos de auditoría)
        resumen = df_h.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento'] = resumen['Excedente'] * COSTO_MINUTO

        st.dataframe(df_h.drop(columns=['Fecha_dt']), use_container_width=True)
        st.table(resumen)
        st.metric("Total a Descontar", f"S/ {resumen['Descuento'].sum():.2f}")
