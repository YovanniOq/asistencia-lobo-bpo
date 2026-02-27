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

# --- 3. FUNCIÓN DE REGISTRO ---
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
        time.sleep(1)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 4. INTERFAZ ---
modo = "Marcación"
with st.sidebar:
    # --- EL LOBO AZUL (IMAGEN INCRUSTADA) AL COSTADO DE GESTIÓN LOBO ---
    st.markdown("""
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 20px;'>
            <img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAACCCAMAAACp8v9fAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAlQTFRF////3+DfpKSkqf99AAAAAAAAsX5zVAAAAAN0Uk5T//8A18o9BAAAAI9JREFUeNrs2MENwCAQA0FX6L9pE0hIn70DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DInZIn60DAgYAn/YCH9mPqXMAAAAASUVORK5CYII=' 
                 style='width: 45px; height: auto;'>
            <h1 style='color: #1E3A8A; font-size: 24px; margin: 0; white-space: nowrap;'>Gestión Lobo</h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# Cabecera principal
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo_lobo.png"):
        st.image("logo_lobo.png", width=150)
with c2:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 40px; margin-bottom: 0;'>Marcación Sr. Lobo</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #444; margin-top: -10px;'>Sr. Lobo BPO Solutions</h3>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        st.cache_data.clear()
        try:
            df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
            emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 INGRESO", use_container_width=True):
                        registrar_en_nube(dni_in, nombre, "INGRESO")
                with col2:
                    if st.button("📤 SALIDA", use_container_width=True):
                        registrar_en_nube(dni_in, nombre, "SALIDA")
            else:
                st.error("DNI no registrado.")
        except FileNotFoundError:
            st.error("Falta archivo empleados.csv")

else: # --- PANEL ADMIN ---
    st.header("📋 Resumen Mensual")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        df_mes = df_h[df_h['Fecha_dt'].dt.month == obtener_hora_peru().month].copy()

        resumen = df_mes.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento'] = resumen['Excedente'] * COSTO_MINUTO

        st.dataframe(df_mes.drop(columns=['Fecha_dt']), use_container_width=True)
        st.subheader("💰 Resumen de Descuentos")
        st.table(resumen)
