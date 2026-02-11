import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00"
TOLERANCIA_MIN = 30
LOGO_ARCHIVO = "logo_lobo.png"

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. INTERFAZ Y DISEÑO ---
st.set_page_config(page_title="Asistencia Sr. Lobo", layout="wide")

# Script para el Foco Automático
components.html("""
    <script>
    function setFocus(){
        var ins = window.parent.document.querySelectorAll('input[type="text"]');
        if(ins.length > 0) { ins[0].focus(); }
    }
    setInterval(setFocus, 1000);
    </script>
""", height=0)

# Encabezado: Logo Izquierda y Título Costado
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=220)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; font-size: 42px; margin-top: 20px;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
    st.write(f"🕒 Hora actual: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("Error en Secrets. Revisa la configuración en Streamlit Cloud.")

# Barra lateral
with st.sidebar:
    st.title("🐺 Gestión")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])

# --- 4. LÓGICA DE REGISTRO ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        df_act = conn.read(spreadsheet=url_hoja, ttl=0)
        ahora = obtener_hora_peru()
        hora_act = ahora.strftime("%H:%M:%S")
        tardanza = 0
        if tipo == "INGRESO":
            t_m = datetime.strptime(hora_act, "%H:%M:%S")
            t_o = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S")
            if t_m > t_o:
                tardanza = max(0, int((t_m - t_o).total_seconds() / 60) - TOLERANCIA_MIN)
        
        nueva = pd.DataFrame([{"DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"), "Hora": hora_act, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza}])
        df_final = pd.concat([df_act, nueva], ignore_index=True)
        conn.update(spreadsheet=url_hoja, data=df_final)
        st.success(f"✅ {tipo} guardado correctamente.")
        time.sleep(1); st.session_state.reset_key += 1; st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# --- 5. MÓDULOS ---
if modo == "Marcación":
    df_empleados = pd.read_csv("empleados.csv")
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
    
    # Caja chica de DNI (solo ocupa una parte de la pantalla)
    c_dni, c_vacio = st.columns([1, 3])
    with c_dni:
        dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.markdown(f"<h2 style='color: #2E7D32;'>👤 Bienvenido: {nombre}</h2>", unsafe_allow_html=True)
            
            try:
                df_cloud = conn.read(spreadsheet=url_hoja, ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs = df_cloud[(df_cloud['DNI'].astype(str) == str(dni)) & (df_cloud['Fecha'] == hoy)]
                est = marcs.iloc[-1]['Tipo'] if not marcs.empty else "SIN MARCAR"

                if est == "SALIDA":
                    st.warning("🚫 Turno finalizado por hoy.")
                    time.sleep(2); st.session_state.reset_key += 1; st.rerun()
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR"), use_container_width=True):
                            registrar_en_nube(dni, nombre, "INGRESO")
                    with c2:
                        if st.button("🚶 PERMISO", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            st.session_state.mostrando_obs = True; st.rerun()
                    with c3:
                        if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_en_nube(dni, nombre, "RETORNO_PERMISO")
                    with c4:
                        if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            registrar_en_nube(dni, nombre, "SALIDA")

                    if st.session_state.mostrando_obs:
                        motivo = st.text_input("MOTIVO DEL PERMISO:")
                        if motivo:
                            registrar_en_nube(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                            st.session_state.mostrando_obs = False
            except:
                st.error("Error de conexión. Verifica permisos en Google Sheets.")
        else:
            st.error("DNI no registrado.")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Historial Mensual":
    st.header("📊 Historial General (Google Sheets)")
    try:
        df_nube = conn.read(spreadsheet=url_hoja, ttl=0)
        st.dataframe(df_nube, use_container_width=True)
    except:
        st.error("No se pudo cargar el historial.")
