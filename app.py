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

# SCRIPT DE FOCO AUTOMÁTICO (Cursor siempre en DNI)
components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0) {
            inputs[0].focus();
        }
    }
    // Reintenta poner el foco cada segundo para asegurar que funcione
    setInterval(setFocus, 1000);
    </script>
""", height=0)

# ESTILO PERSONALIZADO PARA LETRAS GRANDES
st.markdown("""
    <style>
    .titulo-grande {
        font-size: 45px !important;
        font-weight: bold;
        color: #1E3A8A;
        margin-top: 10px;
    }
    .subtitulo {
        font-size: 20px;
        color: #555;
    }
    </style>
""", unsafe_allow_html=True)

# ENCABEZADO: LOGO A LA IZQUIERDA Y TÍTULO AL COSTADO
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, width=220) # Logo grande
with col_titulo:
    st.markdown('<p class="titulo-grande">SR. LOBO BPO SOLUTIONS SAC</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitulo">🕒 Hora actual: <b>{obtener_hora_peru().strftime("%H:%M:%S")}</b></p>', unsafe_allow_html=True)

st.divider()

# BARRA LATERAL (Sidebar)
with st.sidebar:
    st.title("🐺 Gestión")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        password = st.text_input("Contraseña:", type="password")
        if password == "Lobo2026":
            modo = st.sidebar.radio("Módulo:", ["Marcación", "Historial Mensual"])

# --- 3. LÓGICA DE CONEXIÓN Y MARCACIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    ID_HOJA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("⚠️ Error en configuración de Google Sheets.")

if modo == "Marcación":
    # CARGAR EMPLEADOS
    df_empleados = pd.read_csv("empleados.csv")

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    # CAMPO DNI
    dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_{st.session_state.reset_key}")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.markdown(f"<h2 style='color: #2E7D32;'>👤 Bienvenido: {nombre}</h2>", unsafe_allow_html=True)
            
            try:
                # Consultar historial en Google Sheets
                df_hoy = conn.read(spreadsheet=ID_HOJA, ttl=0)
                hoy_fecha = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs = df_hoy[(df_hoy['DNI'].astype(str) == str(dni)) & (df_hoy['Fecha'] == hoy_fecha)]
                est = marcs.iloc[-1]['Tipo'] if not marcs.empty else "SIN MARCAR"

                if est == "SALIDA":
                    st.warning("🚫 Ya registraste tu salida final hoy.")
                    time.sleep(2); st.session_state.reset_key += 1; st.rerun()
                else:
                    # BOTONES DE ACCIÓN (Restaurados todos)
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
                st.error("Error al leer la base de datos de Google.")
        else:
            st.error("DNI no registrado.")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Historial Mensual":
    st.header("📊 Reporte en la Nube")
    df_nube = conn.read(spreadsheet=ID_HOJA, ttl=0)
    st.dataframe(df_nube, use_container_width=True)

# Función interna para registrar
def registrar_en_nube(dni, nombre, tipo, obs=""):
    df_actual = conn.read(spreadsheet=ID_HOJA, ttl=0)
    ahora = obtener_hora_peru()
    hora_actual = ahora.strftime("%H:%M:%S")
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_actual, "%H:%M:%S")
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S")
        if t_marcada > t_oficial:
            tardanza = max(0, int((t_marcada - t_oficial).total_seconds() / 60) - TOLERANCIA_MIN)

    nueva_fila = pd.DataFrame([{
        "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
        "Hora": hora_actual, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza
    }])
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    conn.update(spreadsheet=ID_HOJA, data=df_final)
    st.success(f"✅ {tipo} guardado.")
    time.sleep(1); st.session_state.reset_key += 1; st.rerun()
