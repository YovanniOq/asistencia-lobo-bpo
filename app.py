import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
COSTO_MINUTO = 0.15  
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MENSUAL = 30 

# --- ESTILOS CSS: LOGOS LIMPIOS Y AJUSTE DE ALTURA ---
st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.94);
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
    }
    img {
        background-color: transparent !important;
        mix-blend-mode: multiply;
        border: none !important;
    }
    .sidebar-brand-horizontal {
        display: flex;
        align-items: center; gap: 15px; margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 3. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    st.markdown("<div class='sidebar-brand-horizontal'>", unsafe_allow_html=True)
    c_side_logo, c_side_text = st.columns([0.35, 0.65])
    with c_side_logo:
        if os.path.exists("Lobo.png"): st.image("Lobo.png", width=55)
    with c_side_text:
        st.markdown("<h2 style='color: #1E3A8A; font-size: 21px; margin: 0; padding-top: 15px;'>Gestión Lobo</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    # Guardamos el estado del checkbox para controlar el foco
    acceso_admin = st.checkbox("Acceso Administrador")
    
    if acceso_admin:
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# --- JAVASCRIPT DE FOCO INTELIGENTE MEJORADO ---
# SOLO se activa si NO hemos marcado el checkbox de administrador
if not acceso_admin:
    components.html("""
        <script>
        const forceFocus = () => {
            const inputs = window.parent.document.querySelectorAll('input[type="text"]');
            const passInputs = window.parent.document.querySelectorAll('input[type="password"]');
            
            if (inputs.length > 0) {
                const dniInput = inputs[0];
                const activeElem = window.parent.document.activeElement;
                
                // Si el usuario está en un campo de texto y no es el DNI, y no hay passwords activos
                if (activeElem !== dniInput && passInputs.length === 0) {
                    dniInput.focus();
                }
            }
        };
        setInterval(forceFocus, 1000);
        </script>
    """, height=0)

# --- 4. CABECERA PRINCIPAL (LOGO ELEVADO) ---
c_izq, c_logo_p, c_tit, c_der = st.columns([0.5, 3.5, 6, 0.5])
with c_logo_p:
    if os.path.exists("logo_lobo.png"):
        st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
        st.image("logo_lobo.png", width=320)
        st.markdown("</div>", unsafe_allow_html=True)
with c_tit:
    st.markdown("""
        <div style='padding-top: 15px;'>
            <h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>Marcación Sr. Lobo</h1>
            <h2 style='color: #444; font-size: 26px; margin-top: -10px;'>Sr. Lobo BPO Solutions</h2>
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
            c1, c2 = st.columns(2)
            with c1: st.button("📥 INGRESO", use_container_width=True)
            with c2: st.button("📤 SALIDA", use_container_width=True)
            c3, c4 = st.columns(2)
            with c3: st.button("🚶 SALIDA PERMISO", use_container_width=True)
            with c4: st.button("🏠 ENTRADA PERMISO", use_container_width=True)
        else:
            st.error("DNI no registrado.")

else: # --- PANEL ADMIN ---
    st.header("📋 Reporte Auditado de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
        
        f1, f2, f3 = st.columns(3)
        with f1: sel_anio = st.selectbox("Año", sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True))
        with f2:
            m_num = sorted(df_h[df_h['Fecha_dt'].dt.year == sel_anio]['Fecha_dt'].dt.month.unique())
            sel_mes = st.selectbox("Mes", m_num, format_func=lambda x: meses_dict[x])
        with f3:
            nombres = sorted(df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]['Nombre'].unique())
            sel_nombre = st.selectbox("Trabajador", ["TODOS"] + nombres)
        
        df_f = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)].copy()
        if sel_nombre != "TODOS":
            df_f = df_f[df_f['Nombre'] == sel_nombre]

        st.dataframe(df_f.drop(columns=['Fecha_dt']), use_container_width=True)
        
        st.subheader("💰 Resumen de Auditoría")
        resumen = df_f.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento (S/)'] = resumen['Excedente'] * COSTO_MINUTO
        
        st.table(resumen)
        st.metric("Total General a Descontar", f"S/ {resumen['Descuento (S/)'].sum():.2f}")
