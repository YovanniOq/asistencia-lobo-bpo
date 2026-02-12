import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
LOGO_ARCHIVO = "logo_lobo.png"
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. CONFIGURACIÓN DE PÁGINA Y FOCO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') {
            inputs[0].focus();
        }
    }
    setInterval(setFocus, 500);
    </script>
""", height=0)

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. ESTADOS DE MEMORIA (CRÍTICO) ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False
if "ultimo_estado_local" not in st.session_state: st.session_state.ultimo_estado_local = {}

# --- 5. FUNCIÓN DE GUARDADO ---
def registrar_dato(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Guardar en memoria local antes que en la nube para que la interfaz sea instantánea
        st.session_state.ultimo_estado_local[str(dni)] = tipo
        
        df_actual = conn.read(spreadsheet=url_ho_worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ REGISTRADO: {tipo}")
        time.sleep(1)
        
        if tipo != "SALIDA_PERMISO": # Si es permiso, no reseteamos el DNI para que pueda escribir el motivo
            st.session_state.reset_key += 1
            st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        # Bypass error 200
        st.session_state.ultimo_estado_local[str(dni)] = tipo
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()

# --- 6. MENÚ LATERAL ---
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Completo"])

# --- 7. DISEÑO PRINCIPAL ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO): st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 3])
    with c_dni:
        dni_in = st.text_input("", key=f"in_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni_in:
        df_emp = pd.read_csv("empleados.csv")
        emp = df_emp[df_emp['DNI'].astype(str) == str(dni_in)]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # PRIORIDAD 1: MEMORIA LOCAL (Instantánea)
            # PRIORIDAD 2: NUBE (Si no hay nada en memoria local)
            ultimo = st.session_state.ultimo_estado_local.get(str(dni_in), "NADA")
            
            if ultimo == "NADA":
                try:
                    df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                    hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                    marcs_hoy = df_cloud[(df_cloud['DNI'].astype(str) == str(dni_in)) & (df_cloud['Fecha'] == hoy)]
                    if not marcs_hoy.empty:
                        ultimo = marcs_hoy.iloc[-1]['Tipo']
                except:
                    pass

            col1, col2, col3, col4 = st.columns(4)
            with col1: # INGRESO
                st.button("📥 INGRESO", disabled=(ultimo in ["INGRESO", "RETORNO_PERMISO", "SALIDA_PERMISO"]), 
                          use_container_width=True, on_click=registrar_dato, args=(dni_in, nombre, "INGRESO"))
            
            with col2: # PERMISO
                if st.button("🚶 PERMISO", disabled=(ultimo == "SALIDA_PERMISO" or ultimo == "NADA"), use_container_width=True):
                    st.session_state.mostrar_obs = True
                    st.rerun()
            
            with col3: # RETORNO
                st.button("🔙 RETORNO", disabled=(ultimo != "SALIDA_PERMISO"), 
                          use_container_width=True, on_click=registrar_dato, args=(dni_in, nombre, "RETORNO_PERMISO"))
            
            with col4: # SALIDA
                st.button("📤 SALIDA", disabled=(ultimo == "NADA" or ultimo == "SALIDA"), 
                          use_container_width=True, on_click=registrar_dato, args=(dni_in, nombre, "SALIDA"))

            if st.session_state.mostrar_obs:
                st.divider()
                motivo = st.text_input("ESCRIBA EL MOTIVO DEL PERMISO Y ENTER:")
                if motivo:
                    registrar_dato(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
        else:
            st.error("DNI no registrado.")

elif modo == "Historial Completo":
    st.header("📋 Historial en Drive")
    try:
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        st.dataframe(df_h, use_container_width=True)
    except:
        st.warning("Cargando historial...")
