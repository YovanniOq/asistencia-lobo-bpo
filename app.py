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

# Script para el Foco Automático en el DNI
components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0) { inputs[0].focus(); }
    }
    setInterval(setFocus, 1000);
    </script>
""", height=0)

# CSS para mejorar el tamaño de los textos
st.markdown("""
    <style>
    .main-title { font-size: 42px !important; font-weight: bold; color: #1E3A8A; margin-bottom: 0px; }
    .status-text { font-size: 18px; color: #555; }
    </style>
""", unsafe_allow_html=True)

# ENCABEZADO: Logo y Título alineados
col_head1, col_head2 = st.columns([1, 4])
with col_head1:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=200)
with col_head2:
    st.markdown('<p class="main-title">SR. LOBO BPO SOLUTIONS SAC</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="status-text">🕒 Hora actual: <b>{obtener_hora_peru().strftime("%H:%M:%S")}</b></p>', unsafe_allow_html=True)

st.divider()

# --- 3. LÓGICA DE CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("⚠️ Error crítico en los Secrets de Streamlit.")

# BARRA LATERAL
with st.sidebar:
    st.title("🐺 Menú Gestión")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial"])

if modo == "Marcación":
    df_empleados = pd.read_csv("empleados.csv")
    
    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    # CAJA DE DNI COMPACTA (Usando columnas para centrarla y achicarla)
    st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
    c_dni1, c_dni2, c_dni3 = st.columns([1, 1, 2]) # El DNI ahora solo ocupa una fracción
    with c_dni1:
        dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.markdown(f"<h2 style='color: #2E7D32;'>👤 Bienvenido: {nombre}</h2>", unsafe_allow_html=True)
            
            try:
                # Lectura de la base de datos en la nube
                df_cloud = conn.read(spreadsheet=url_hoja, ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs = df_cloud[(df_cloud['DNI'].astype(str) == str(dni)) & (df_cloud['Fecha'] == hoy)]
                est = marcs.iloc[-1]['Tipo'] if not marcs.empty else "SIN MARCAR"

                if est == "SALIDA":
                    st.warning("🚫 Turno finalizado por hoy.")
                    time.sleep(2); st.session_state.reset_key += 1; st.rerun()
                else:
                    # BOTONES DE ACCIÓN
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR"), use_container_width=True):
                            registrar_en_nube(dni, nombre, "INGRESO", url_hoja, conn)
                    with b2:
                        if st.button("🚶 PERMISO", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            st.session_state.mostrando_obs = True; st.rerun()
                    with b3:
                        if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_en_nube(dni, nombre, "RETORNO_PERMISO", url_hoja, conn)
                    with b4:
                        if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            registrar_en_nube(dni, nombre, "SALIDA", url_hoja, conn)

                    if st.session_state.mostrando_obs:
                        motivo = st.text_input("MOTIVO DEL PERMISO:")
                        if motivo:
                            registrar_en_nube(dni, nombre, "SALIDA_PERMISO", url_hoja, conn, obs=motivo)
                            st.session_state.mostrando_obs = False
            except:
                st.error("Error al leer la base de datos de Google. Verifica los permisos de editor en la hoja.")
        else:
            st.error("DNI no registrado.")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

def registrar_en_nube(dni, nombre, tipo, url, con_obj, obs=""):
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
        st.success(f"✅ {tipo} guardado correctamente.")
        time.sleep(1); st.session_state.reset_key += 1; st.rerun()
    except:
        st.error("Error al guardar los datos.")

elif modo == "Historial":
    st.header("📊 Reporte en Google Sheets")
    st.dataframe(conn.read(spreadsheet=url_hoja, ttl=0), use_container_width=True)
