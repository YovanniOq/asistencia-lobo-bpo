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

# Intentar conectar usando el ID exacto de los Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    ID_HOJA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Error en la configuración de los Secrets. Revisa el ID de la hoja.")

def registrar_evento(dni, nombre, tipo, obs=""):
    df_actual = conn.read(spreadsheet=ID_HOJA, ttl=0)
    ahora = obtener_hora_peru()
    hora_str = ahora.strftime("%H:%M:%S")
    fecha_str = ahora.strftime("%Y-%m-%d")
    
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_str, "%H:%M:%S")
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S")
        if t_marcada > t_oficial:
            dif = int((t_marcada - t_oficial).total_seconds() / 60)
            if dif > TOLERANCIA_MIN:
                tardanza = dif

    nueva_fila = pd.DataFrame([{
        "DNI": str(dni), "Nombre": nombre, "Fecha": fecha_str,
        "Hora": hora_str, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza
    }])
    
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    conn.update(spreadsheet=ID_HOJA, data=df_final)
    st.success(f"✅ {tipo} registrado correctamente.")

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Asistencia Sr. Lobo", layout="wide")

# SCRIPT DE FOCO AUTOMÁTICO (Más agresivo para que no falle)
components.html("""
    <script>
    const setFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0) inputs[0].focus();
    }
    setInterval(setFocus, 500);
    </script>
""", height=0)

# BARRA LATERAL
with st.sidebar:
    st.title("🐺 Panel de Control")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        password = st.text_input("Contraseña:", type="password")
        if password == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])

if modo == "Marcación":
    # DISEÑO DE CABECERA: Logo y Letras grandes
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        if os.path.exists(LOGO_ARCHIVO):
            # Forzamos el tamaño del logo a 250px para que se vea imponente
            st.image(LOGO_ARCHIVO, width=250)
    with col_titulo:
        # Usamos HTML para letras más grandes y negritas
        st.markdown("""
            <h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>
                SR. LOBO BPO SOLUTIONS SAC
            </h1>
            <p style='font-size: 24px; color: #555;'>Sistema de Asistencia en Tiempo Real</p>
        """, unsafe_allow_html=True)
        st.write(f"### 🕒 Hora actual: **{obtener_hora_peru().strftime('%H:%M:%S')}**")
    
    st.divider()

    # CARGAR EMPLEADOS
    df_empleados = pd.read_csv("empleados.csv")

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    # CAJA DE DNI (Aumentamos el tamaño visual con markdown arriba)
    st.markdown("### DIGITE SU DNI Y PRESIONE ENTER:")
    dni = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.markdown(f"<h2 style='text-align: center; color: green;'>👤 Bienvenido: {nombre}</h2>", unsafe_allow_html=True)
            
            # Consultar último estado en Google Sheets
            try:
                df_hoy = conn.read(spreadsheet=ID_HOJA, ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs = df_hoy[(df_hoy['DNI'].astype(str) == str(dni)) & (df_hoy['Fecha'] == hoy)]
                est = marcs.iloc[-1]['Tipo'] if not marcs.empty else "SIN MARCAR"

                if est == "SALIDA":
                    st.warning("🚫 Turno finalizado por hoy.")
                    time.sleep(2); st.session_state.reset_key += 1; st.rerun()
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR"), use_container_width=True):
                            registrar_evento(dni, nombre, "INGRESO")
                            time.sleep(1); st.session_state.reset_key += 1; st.rerun()
                    with c2:
                        if st.button("🚶 PERMISO", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            st.session_state.mostrando_obs = True; st.rerun()
                    with c3:
                        if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_evento(dni, nombre, "RETORNO_PERMISO")
                            time.sleep(1); st.session_state.reset_key += 1; st.rerun()
                    with c4:
                        if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                            registrar_evento(dni, nombre, "SALIDA")
                            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

                    if st.session_state.mostrando_obs:
                        motivo = st.text_input("Escriba el MOTIVO del permiso:")
                        if motivo:
                            registrar_evento(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                            st.session_state.mostrando_obs = False
                            time.sleep(1); st.session_state.reset_key += 1; st.rerun()
            except:
                st.error("Error al conectar con la base de datos de Google.")
        else:
            st.error("DNI no registrado.")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Historial Mensual":
    st.header("📊 Historial General")
    df_nube = conn.read(spreadsheet=ID_HOJA, ttl=0)
    st.dataframe(df_nube, use_container_width=True)
