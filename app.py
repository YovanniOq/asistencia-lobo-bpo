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

# --- JAVASCRIPT DE FOCO INTELIGENTE MEJORADO ---
# Ahora respeta si el usuario está en el campo de PASSWORD o OBSERVACIONES
components.html("""
    <script>
    const forceFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        const passInputs = window.parent.document.querySelectorAll('input[type="password"]');
        
        if (inputs.length > 0) {
            const dniInput = inputs[0];
            const activeElem = window.parent.document.activeElement;
            
            // Detectar si el usuario está en la caja de observaciones (segundo input de texto)
            const escribiendoObservacion = inputs.length > 1 && activeElem === inputs[1];
            
            // Detectar si el usuario está en la caja de contraseña
            let escribiendoPassword = false;
            passInputs.forEach(p => { if(activeElem === p) escribiendoPassword = true; });

            // Solo forzar foco al DNI si NO estamos en password ni en observaciones
            if (activeElem !== dniInput && !escribiendoPassword && !escribiendoObservacion) {
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
            "DNI": str(dni).strip(), 
            "Nombre": nombre, 
            "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), 
            "Tipo": tipo, 
            "Observacion": obs, 
            "Tardanza_Min": tardanza_min, 
            "Descuento_Soles": descuento
        }])
        
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
    if st.checkbox("Acceso Administrador"):
        # El JS ahora permitirá escribir aquí sin saltar al DNI
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            st.info("Modo Admin: Historial disponible abajo.")

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=120)
with col2:
    st.markdown("<h1 style='color: #1E3A8A; margin-bottom: 0;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

st.write("### DIGITE SU DNI:")
c_dni, _ = st.columns([1, 4])
with c_dni:
    dni_in = st.text_input("DNI_BOX", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

if dni_in:
    st.cache_data.clear()
    try:
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            df_h['DNI'] = df_h['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            regs = df_h[(df_h['DNI'] == str(dni_in).strip()) & (df_h['Fecha'] == hoy)]
            u_tipo = str(regs.iloc[-1]['Tipo']).strip().upper() if not regs.empty else "NADA"

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, disabled=(u_tipo != "NADA")):
                    registrar_en_nube(dni_in, nombre, "INGRESO")
            
            esta_dentro = (u_tipo == "INGRESO" or u_tipo == "RETORNO_PERMISO")
            with c2:
                if st.button("🚶 PERMISO", use_container_width=True, disabled=not esta_dentro):
                    st.session_state.mostrar_obs = True
                    st.rerun()
            with c3:
                if st.button("🔙 RETORNO", use_container_width=True, disabled=(u_tipo != "SALIDA_PERMISO")):
                    registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
            with c4:
                if st.button("📤 SALIDA", use_container_width=True, disabled=not esta_dentro):
                    registrar_en_nube(dni_in, nombre, "SALIDA")

            if st.session_state.mostrar_obs:
                st.divider()
                motivo = st.text_input("MOTIVO DEL PERMISO (ENTER):")
                if motivo: registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
        else:
            st.error("DNI no registrado.")
    except Exception:
        pass
