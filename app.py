import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
ARCHIVO_MARCACIONES = "marcacion.csv"
ARCHIVO_EMPLEADOS = "empleados.csv"
LOGO_NOMBRE = "logo_lobo.png" 
HORA_ENTRADA_OFICIAL = "08:00:00" 
MINUTOS_TOLERANCIA = 30

# FUNCIÓN PARA OBTENER HORA DE PERÚ (UTC-5)
def obtener_hora_peru():
    # Streamlit Cloud usa UTC, restamos 5 horas para Perú
    utc_now = datetime.now(timezone.utc)
    peru_now = utc_now - timedelta(hours=5)
    return peru_now

def inicializar_sistema():
    if not os.path.exists(ARCHIVO_MARCACIONES) or os.stat(ARCHIVO_MARCACIONES).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Fecha", "Hora", "Tipo", "Observacion", "Tardanza_Min"]).to_csv(ARCHIVO_MARCACIONES, index=False)
    if not os.path.exists(ARCHIVO_EMPLEADOS) or os.stat(ARCHIVO_EMPLEADOS).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Salario"]).to_csv(ARCHIVO_EMPLEADOS, index=False)

def obtener_estado_hoy(dni):
    try:
        df = pd.read_csv(ARCHIVO_MARCACIONES)
        hoy = obtener_hora_peru().strftime('%Y-%m-%d')
        reg = df[(df['DNI'].astype(str) == str(dni)) & (df['Fecha'] == hoy)]
        if reg.empty: return "SIN MARCAR"
        return reg.iloc[-1]['Tipo']
    except: return "SIN MARCAR"

def registrar(dni, nombre, tipo, obs=""):
    ahora = obtener_hora_peru()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M:%S")
    
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_actual, '%H:%M:%S')
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, '%H:%M:%S')
        if t_marcada > t_oficial:
            dif = int((t_marcada - t_oficial).total_seconds() / 60)
            if dif > MINUTOS_TOLERANCIA: tardanza = dif

    nueva_fila = {
        "DNI": dni, "Nombre": nombre, "Fecha": fecha_hoy,
        "Hora": hora_actual, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza
    }
    df = pd.read_csv(ARCHIVO_MARCACIONES)
    pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True).to_csv(ARCHIVO_MARCACIONES, index=False)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Sr. Lobo BPO", layout="centered")
inicializar_sistema()
df_empleados = pd.read_csv(ARCHIVO_EMPLEADOS)

# BARRA LATERAL
st.sidebar.title("🐺 Gestión")
acceso_admin = st.sidebar.checkbox("Acceso Administrador")
modo = "Marcación"

if acceso_admin:
    password = st.sidebar.text_input("Contraseña:", type="password")
    if password == "Lobo2026":
        modo = st.sidebar.radio("Módulo:", ["Marcación", "Reporte Nómina"])

if modo == "Marcación":
    col1, col2 = st.columns([1.5, 4])
    with col1:
        if os.path.exists(LOGO_NOMBRE): st.image(LOGO_NOMBRE, width=180)
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>Hora Actual: {obtener_hora_peru().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
    st.divider()

    # SCRIPT DE FOCO INTELIGENTE
    components.html("""<script>function setFocus(){ var ins = window.parent.document.querySelectorAll('input[type="text"]'); if(ins.length===1){ins[0].focus();}else if(ins.length>1){ins[1].focus();}} setInterval(setFocus, 500);</script>""", height=0)

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_{st.session_state.reset_key}")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            est = obtener_estado_hoy(dni)
            if est == "SALIDA":
                st.warning(f"🚫 {nombre}, jornada finalizada.")
                time.sleep(2); st.session_state.reset_key += 1; st.rerun()
            else:
                st.success(f"👤 {nombre} | Estado: {est}")
                c1, c2 = st.columns(2); c3, c4 = st.columns(2)
                with c1:
                    if st.button("📥 INGRESO", use_container_width=True, type="primary", disabled=(est != "SIN MARCAR")):
                        registrar(dni, nombre, "INGRESO"); st.session_state.reset_key += 1; st.rerun()
                with c3:
                    if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(est != "INGRESO" and est != "RETORNO_PERMISO")):
                        st.session_state.mostrando_obs = True; st.rerun()
                if st.session_state.mostrando_obs:
                    motivo = st.text_input("MOTIVO DEL PERMISO:", key=f"mot_{st.session_state.reset_key}")
                    if motivo:
                        registrar(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                        st.session_state.mostrando_obs = False; st.session_state.reset_key += 1; st.rerun()
                with c4:
                    if st.button("🔙 RETORNO PERMISO", use_container_width=True, disabled=(est != "SALIDA_PERMISO")):
                        registrar(dni, nombre, "RETORNO_PERMISO"); st.session_state.reset_key += 1; st.rerun()
                with c2:
                    if st.button("📤 SALIDA FINAL", use_container_width=True, disabled=(est not in ["INGRESO", "RETORNO_PERMISO"])):
                        registrar(dni, nombre, "SALIDA"); st.session_state.reset_key += 1; st.rerun()
        else:
            st.error("DNI no registrado"); time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Reporte Nómina":
    st.header("💰 Resumen de Tardanzas y Descuentos")
    df_m = pd.read_csv(ARCHIVO_MARCACIONES)
    df_reporte = df_m.merge(df_empleados, on="DNI", how="left")
    df_reporte['Equivalente_Dinero'] = (df_reporte['Salario'] / 30 / 8 / 60) * df_reporte['Tardanza_Min']
    df_reporte['Equivalente_Dinero'] = df_reporte['Equivalente_Dinero'].round(2)
    columnas_vista = ['Fecha', 'Nombre_x', 'Hora', 'Tipo', 'Tardanza_Min', 'Equivalente_Dinero', 'Observacion']
    st.dataframe(df_reporte[columnas_vista], use_container_width=True)
    csv = df_reporte[columnas_vista].to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Reporte", data=csv, file_name="Reporte_Lobo_BPO.csv", use_container_width=True)
