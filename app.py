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

# --- ESTILOS CSS: FONDO, MARCA DE AGUA Y AJUSTE DE CABECERA ---
st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 3rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        position: relative;
    }
    /* Marca de agua sutil */
    .main .block-container::before {
        content: "";
        position: absolute;
        top: 50%; left: 50%;
        width: 500px; height: 500px;
        background-image: url("https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        opacity: 0.04; 
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 0;
    }
    /* AJUSTE PARA BAJAR EL LOGO Y ALINEARLO CON EL TÍTULO */
    .header-logo-container {
        padding-top: 35px; /* Baja el logo para que no esté pegado arriba */
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

# --- 3. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    c_logo_side, c_text_side = st.columns([0.2, 0.8])
    with c_logo_side:
        if os.path.exists("Lobo.png"): st.image("Lobo.png", width=32)
    with c_text_side:
        st.markdown("<h2 style='color: #1E3A8A; font-size: 20px; margin: 0; padding-top: 5px;'>Gestión Lobo</h2>", unsafe_allow_html=True)
    
    st.divider()
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# --- 4. CABECERA PRINCIPAL (CON AJUSTE DE ALTURA) ---
c_izq, c_logo_p, c_tit, c_der = st.columns([0.5, 3.5, 6, 0.5])
with c_logo_p:
    if os.path.exists("logo_lobo.png"):
        st.markdown("<div class='header-logo-container'>", unsafe_allow_html=True)
        st.image("logo_lobo.png", width=320)
        st.markdown("</div>", unsafe_allow_html=True)
with c_tit:
    st.markdown(f"""
        <div style='padding-top: 45px;'>
            <h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>Marcación Sr. Lobo</h1>
            <h3 style='color: #444; font-size: 26px; margin-top: -10px;'>Sr. Lobo BPO Solutions</h3>
        </div>
    """, unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 4])
    with c_dni:
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
                if st.button("📥 INGRESO", use_container_width=True): st.success(f"INGRESO: {nombre}")
            with c_btns[1]:
                if st.button("📤 SALIDA", use_container_width=True): st.success(f"SALIDA: {nombre}")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN CON FILTROS ---
    st.header("📋 Reporte Auditado de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
        
        f1, f2, f3 = st.columns(3)
        with f1:
            anios = sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True)
            sel_anio = st.selectbox("Año", anios)
        with f2:
            meses_num = sorted(df_h[df_h['Fecha_dt'].dt.year == sel_anio]['Fecha_dt'].dt.month.unique())
            sel_mes = st.selectbox("Mes", meses_num, format_func=lambda x: meses_dict[x])
        with f3:
            nombres = sorted(df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]['Nombre'].unique())
            sel_nombre = st.selectbox("Trabajador", ["TODOS"] + nombres)
        
        df_filtrado = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)].copy()
        
        resumen = df_filtrado.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento'] = resumen['Excedente'] * COSTO_MINUTO

        if sel_nombre != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Nombre'] == sel_nombre]
            resumen = resumen[resumen['Nombre'] == sel_nombre]

        st.dataframe(df_filtrado.drop(columns=['Fecha_dt']), use_container_width=True)
        st.table(resumen)
        st.metric("Total a Descontar", f"S/ {resumen['Descuento'].sum():.2f}")
