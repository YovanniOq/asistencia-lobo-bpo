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

# --- 2. INTERFAZ Y ESTILO ---
st.set_page_config(page_title="Asistencia Sr. Lobo", layout="wide")

# Foco automático en el DNI
components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0) { inputs[0].focus(); }
    }
    setInterval(setFocus, 1000);
    </script>
""", height=0)

# Estilo para el título grande
st.markdown("<style>.main-title { font-size: 40px !important; font-weight: bold; color: #1E3A8A; }</style>", unsafe_allow_html=True)

# ENCABEZADO: Logo y Título juntos
col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=220)
with col_h2:
    st.markdown('<p class="main-title">SR. LOBO BPO SOLUTIONS SAC</p>', unsafe_allow_html=True)
    st.write(f"🕒 Hora actual: **{obtener_hora_peru().strftime('%H:%M:%S')}**")

st.divider()

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("Error en Secrets.")

# Menú Lateral
with st.sidebar:
    st.title("🐺 Gestión")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial"])

# --- 4. MÓDULOS ---
if modo == "Marcación":
    df_empleados = pd.read_csv("empleados.csv")
    
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
    
    # CAJA CHICA: Usamos columnas para que el input sea pequeño
    c_input, c_espacio = st.columns([1, 3]) 
    with c_input:
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
                    st.warning("🚫 Turno finalizado hoy.")
                    time.sleep(2); st.session_state.reset_key += 1; st.rerun()
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR"), use_container_width=True):
                            registrar_dato(dni, nombre, "INGRESO", url_hoja, conn)
                    with c2:
                        if st.button("🚶 PERMISO", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            st.session_state.mostrando_obs = True; st.rerun()
                    with c3:
                        if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_dato(dni, nombre, "RETORNO_PERMISO", url_hoja, conn)
                    with c4:
                        if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            registrar_dato(dni, nombre, "SALIDA", url_hoja, conn)

                    if st.session_state.mostrando_obs:
                        motivo = st.text_input("MOTIVO DEL PERMISO:")
                        if motivo:
                            registrar_dato(dni, nombre, "SALIDA_PERMISO", url_hoja, conn, obs=motivo)
                            st.session_state.mostrando_obs = False
            except:
                st.error("Error al leer Google Sheets. Verifica permisos.")
        else:
            st.error("DNI no registrado.")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Historial":
    st.header("📊 Historial General")
    st.dataframe(conn.read(spreadsheet=url_hoja, ttl=0), use_container_width=True)

# Función de registro (Fuera de los bloques if/elif)
def registrar_dato(dni, nombre, tipo, url, con_obj, obs=""):
    try:
        df_act = con_obj.read(spreadsheet=url, ttl=0)
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
        con_obj.update(spreadsheet=url, data=df_final)
        st.success(f"✅ {tipo} guardado.")
        time.sleep(1); st.session_state.reset_key += 1; st.rerun()
    except:
        st.error("Error al guardar.")
