import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
ARCHIVO_MARCACIONES = "marcacion.csv"
ARCHIVO_EMPLEADOS = "empleados.csv"
LOGO_NOMBRE = "logo_lobo.png" 

def inicializar_sistema():
    if not os.path.exists(ARCHIVO_MARCACIONES) or os.stat(ARCHIVO_MARCACIONES).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Fecha", "Hora", "Tipo", "Observacion", "Tardanza_Min"]).to_csv(ARCHIVO_MARCACIONES, index=False)
    if not os.path.exists(ARCHIVO_EMPLEADOS) or os.stat(ARCHIVO_EMPLEADOS).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Salario"]).to_csv(ARCHIVO_EMPLEADOS, index=False)

def obtener_ultimo_registro(dni):
    try:
        df = pd.read_csv(ARCHIVO_MARCACIONES)
        hoy = datetime.now().strftime('%Y-%m-%d')
        reg = df[(df['DNI'].astype(str) == str(dni)) & (df['Fecha'] == hoy)]
        return reg.iloc[-1] if not reg.empty else None
    except: return None

def registrar(dni, nombre, tipo, obs="", tardanza=0):
    ahora = datetime.now()
    nueva_fila = {
        "DNI": dni, "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
        "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, 
        "Tardanza_Min": tardanza
    }
    df = pd.read_csv(ARCHIVO_MARCACIONES)
    pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True).to_csv(ARCHIVO_MARCACIONES, index=False)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Sr. Lobo BPO", layout="centered")
inicializar_sistema()
df_empleados = pd.read_csv(ARCHIVO_EMPLEADOS)

# BARRA LATERAL PROTEGIDA (Ocultar Nómina para empleados)
st.sidebar.title("🐺 Gestión")
acceso_admin = st.sidebar.checkbox("Acceso Administrador")
modo = "Marcación"

if acceso_admin:
    password = st.sidebar.text_input("Contraseña:", type="password")
    if password == "Lobo2026": # TU CLAVE PRIVADA
        modo = st.sidebar.radio("Módulo:", ["Marcación", "Reporte Nómina"])
    elif password != "":
        st.sidebar.error("Clave incorrecta")

if modo == "Marcación":
    # ENCABEZADO: Lobo más grande (col 1.5) y Texto centro
    col1, col2 = st.columns([1.5, 4])
    with col1:
        if os.path.exists(LOGO_NOMBRE):
            st.image(LOGO_NOMBRE, width=180) # Logo más grande
        else:
            st.write("🐺")
            
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1E3A8A; font-family: Arial; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-weight: bold;'>CONTROL DE ASISTENCIA</p>", unsafe_allow_html=True)
    
    st.divider()

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False
    
    # FOCO AUTOMÁTICO
    components.html(f"""<script>window.parent.document.querySelectorAll('input[type="text"]')[0].focus();</script>""", height=0)

    dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_{st.session_state.reset_key}")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            ult = obtener_ultimo_registro(dni)
            est = ult['Tipo'] if ult is not None else "SIN MARCAR"
            
            st.success(f"👤 {nombre} | Estado: {est}")
            
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)

            with c1:
                if st.button("📥 INGRESO", use_container_width=True, type="primary", disabled=(est != "SIN MARCAR")):
                    registrar(dni, nombre, "INGRESO")
                    st.session_state.reset_key += 1; st.rerun()

            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(est != "INGRESO")):
                    st.session_state.mostrando_obs = True

            if st.session_state.mostrando_obs:
                motivo = st.text_input("MOTIVO DEL PERMISO (Enter):", key=f"mot_{st.session_state.reset_key}")
                if motivo:
                    registrar(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                    st.session_state.mostrando_obs = False
                    st.session_state.reset_key += 1; st.rerun()

            with c4:
                if st.button("🔙 RETORNO PERMISO", use_container_width=True, disabled=(est != "SALIDA_PERMISO")):
                    registrar(dni, nombre, "RETORNO_PERMISO")
                    st.session_state.reset_key += 1; st.rerun()

            with c2:
                if st.button("📤 SALIDA FINAL", use_container_width=True, disabled=(est not in ["INGRESO", "RETORNO_PERMISO"])):
                    registrar(dni, nombre, "SALIDA")
                    st.session_state.reset_key += 1; st.rerun()
        else:
            st.error("DNI no registrado")
            time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Reporte Nómina":
    st.header("💰 Reporte Administrativo")
    df_m = pd.read_csv(ARCHIVO_MARCACIONES)
    st.dataframe(df_m, use_container_width=True)
