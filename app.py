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

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco inteligente
components.html("""
    <script>
    const forceFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if (inputs.length === 1) {
            inputs[0].focus();
        }
    };
    setInterval(forceFocus, 1000);
    </script>
""", height=0)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False

# --- 3. FUNCIÓN DE GRABACIÓN ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        tardanza_min = 0
        descuento = 0
        if tipo == "INGRESO":
            hora_act = ahora.time()
            hora_lim = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if hora_act > hora_lim:
                diff = datetime.combine(datetime.today(), hora_act) - datetime.combine(datetime.today(), hora_lim)
                tardanza_min = int(diff.total_seconds() / 60)
                descuento = round(tardanza_min * COSTO_MINUTO, 2)

        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, 
            "Tardanza_Min": tardanza_min, "Descuento_Soles": descuento
        }])
        
        # Limpiar caché y actualizar
        st.cache_data.clear()
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_h, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.2)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 4. INTERFAZ ---
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = "Historial"

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=150)
with col2:
    st.markdown("<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    dni_in = st.text_input("DNI_INPUT", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")
    
    if dni_in:
        # Forzar lectura fresca de la nube cada vez que se digita el DNI
        st.cache_data.clear()
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # --- BÚSQUEDA DE HISTORIAL BLINDADA ---
            df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            
            # Filtramos por fecha hoy y comparamos DNI como texto para evitar fallos de formato
            df_h['DNI'] = df_h['DNI'].astype(str)
            regs = df_h[(df_h['DNI'] == str(dni_in)) & (df_h['Fecha'] == hoy)]
            
            u_tipo = "NADA"
            if not regs.empty:
                u_tipo = str(regs.iloc[-1]['Tipo']).strip().upper()

            # --- LÓGICA DE BOTONES ---
            c1, c2, c3, c4 = st.columns(4)
            
            # Botón INGRESO: Solo si no hay nada hoy
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, disabled=(u_tipo != "NADA")):
                    registrar_en_nube(dni_in, nombre, "INGRESO")
            
            # Botón PERMISO: Solo si está dentro
            esta_dentro = (u_tipo == "INGRESO" or u_tipo == "RETORNO_PERMISO")
            with c2:
                if st.button("🚶 PERMISO", use_container_width=True, disabled=not esta_dentro):
                    st.session_state.mostrar_obs = True
                    st.rerun()
            
            # Botón RETORNO: Solo si salió a permiso
            with c3:
                if st.button("🔙 RETORNO", use_container_width=True, disabled=(u_tipo != "SALIDA_PERMISO")):
                    registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
            
            # Botón SALIDA: Solo si está dentro
            with c4:
                if st.button("📤 SALIDA", use_container_width=True, disabled=not esta_dentro):
                    registrar_en_nube(dni_in, nombre, "SALIDA")

            if u_tipo == "SALIDA":
                st.warning("⚠️ Ya marcaste tu SALIDA hoy. ¡Buen descanso!")

            if st.session_state.mostrar_obs:
                st.divider()
                motivo = st.text_input("ESCRIBA EL MOTIVO DEL PERMISO:")
                if motivo: registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
        else:
            st.error("DNI no registrado.")
else:
    st.header("Historial")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    st.dataframe(df_h, use_container_width=True)
