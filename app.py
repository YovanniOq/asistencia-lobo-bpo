import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time

# --- 1. CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00"
TOLERANCIA_MIN = 30
LOGO_ARCHIVO = "logo_lobo.png"

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_evento(dni, nombre, tipo, obs=""):
    df_actual = conn.read(ttl=0)
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
    conn.update(data=df_final)
    st.success(f"✅ {tipo} registrado correctamente.")

# --- 2. INTERFAZ (BARRA LATERAL / SIDEBAR) ---
st.set_page_config(page_title="Asistencia Sr. Lobo", layout="wide")

# Todo lo que va en el menú de la izquierda
with st.sidebar:
    if os.path.exists(LOGO_ARCHIVO):
        st.image(LOGO_ARCHIVO, use_container_width=True)
    st.title("🐺 Gestión")
    acceso_admin = st.checkbox("Acceso Administrador")
    modo = "Marcación"
    if acceso_admin:
        password = st.text_input("Contraseña:", type="password")
        if password == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial Mensual"])

# --- 3. CUERPO PRINCIPAL ---
if modo == "Marcación":
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>🕒 Hora actual: <b>{obtener_hora_peru().strftime('%H:%M:%S')}</b></p>", unsafe_allow_html=True)
    st.divider()

    # Cargar empleados
    df_empleados = pd.read_csv("empleados.csv")

    if "mostrando_obs" not in st.session_state:
        st.session_state.mostrando_obs = False

    # Contenedor central para el DNI
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.markdown(f"<h3 style='text-align: center;'>👤 {nombre}</h3>", unsafe_allow_html=True)
            
            # Consultar último estado
            df_hoy = conn.read(ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            marcs = df_hoy[(df_hoy['DNI'].astype(str) == str(dni)) & (df_hoy['Fecha'] == hoy)]
            est = marcs.iloc[-1]['Tipo'] if not marcs.empty else "SIN MARCAR"

            if est == "SALIDA":
                st.warning("🚫 Turno finalizado por hoy.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR"), use_container_width=True):
                        registrar_evento(dni, nombre, "INGRESO")
                        time.sleep(1); st.rerun()
                with c2:
                    if st.button("🚶 PERMISO", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                        st.session_state.mostrando_obs = True
                with c3:
                    if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO"), use_container_width=True):
                        registrar_evento(dni, nombre, "RETORNO_PERMISO")
                        time.sleep(1); st.rerun()
                with c4:
                    if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"]), use_container_width=True):
                        registrar_evento(dni, nombre, "SALIDA")
                        time.sleep(1); st.rerun()

                if st.session_state.mostrando_obs:
                    motivo = st.text_input("MOTIVO DEL PERMISO:")
                    if motivo:
                        registrar_evento(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                        st.session_state.mostrando_obs = False
                        time.sleep(1); st.rerun()
        else:
            st.error("DNI no registrado.")

elif modo == "Historial Mensual":
    st.header("📊 Historial de Marcaciones (Nube)")
    df_nube = conn.read(ttl=0)
    st.dataframe(df_nube, use_container_width=True)
    
    csv = df_nube.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Todo el Historial", data=csv, file_name="asistencia_lobo.csv")
