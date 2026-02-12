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

# Inicializar estados de sesión
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False

# --- 4. FUNCIÓN DE GUARDADO (LA QUE FUNCIONA) ---
def registrar_dato(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Leemos para concatenar
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        
        # Subimos a Drive
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ REGISTRADO: {tipo}")
        st.balloons()
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
        
    except Exception as e:
        if "200" in str(e):
            st.session_state.reset_key += 1
            st.session_state.mostrar_obs = False
            st.rerun()
        else:
            st.error(f"Error: {e}")

# --- 5. MENÚ LATERAL (EL QUE SE OCULTA) ---
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Completo"])
        elif clave != "":
            st.error("Clave incorrecta")

# --- 6. DISEÑO PRINCIPAL ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO): st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

# --- 7. MÓDULOS ---
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
            
            # Consultar nube para bloquear botones
            try:
                df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs_hoy = df_cloud[(df_cloud['DNI'].astype(str) == str(dni_in)) & (df_cloud['Fecha'] == hoy)]
                ya_ingreso = not marcs_hoy[marcs_hoy['Tipo'] == "INGRESO"].empty
                ultimo = marcs_hoy.iloc[-1]['Tipo'] if not marcs_hoy.empty else "NADA"
            except:
                ya_ingreso = False; ultimo = "NADA"

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("📥 INGRESO", disabled=ya_ingreso, use_container_width=True):
                    registrar_dato(dni_in, nombre, "INGRESO")
            with col2:
                if st.button("🚶 PERMISO", disabled=(not ya_ingreso or ultimo == "SALIDA_PERMISO"), use_container_width=True):
                    st.session_state.mostrar_obs = True
                    st.rerun()
            with col3:
                if st.button("🔙 RETORNO", disabled=(ultimo != "SALIDA_PERMISO"), use_container_width=True):
                    registrar_dato(dni_in, nombre, "RETORNO_PERMISO")
            with col4:
                if st.button("📤 SALIDA", disabled=not ya_ingreso, use_container_width=True):
                    registrar_dato(dni_in, nombre, "SALIDA")

            if st.session_state.mostrar_obs:
                st.divider()
                motivo = st.text_input("MOTIVO DEL PERMISO (Escriba y ENTER):")
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
        st.warning("Cargando datos desde Google Drive...")
