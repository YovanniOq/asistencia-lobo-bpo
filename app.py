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
HORA_ENTRADA_OFICIAL = "08:00:00" 
MINUTOS_TOLERANCIA = 30

def inicializar_sistema():
    if not os.path.exists(ARCHIVO_MARCACIONES) or os.stat(ARCHIVO_MARCACIONES).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Fecha", "Hora", "Tipo", "Observacion", "Tardanza_Min"]).to_csv(ARCHIVO_MARCACIONES, index=False)
    if not os.path.exists(ARCHIVO_EMPLEADOS) or os.stat(ARCHIVO_EMPLEADOS).st_size == 0:
        pd.DataFrame(columns=["DNI", "Nombre", "Salario"]).to_csv(ARCHIVO_EMPLEADOS, index=False)

def calcular_tardanza(hora_marcada):
    fmt = '%H:%M:%S'
    t_marcada = datetime.strptime(hora_marcada, fmt)
    t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, fmt)
    
    if t_marcada > t_oficial:
        diferencia_total = int((t_marcada - t_oficial).total_seconds() / 60)
        # Solo hay tardanza si supera la tolerancia de 30 min
        if diferencia_total > MINUTOS_TOLERANCIA:
            return diferencia_total
    return 0 

def registrar(dni, nombre, tipo, obs=""):
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M:%S")
    tardanza = calcular_tardanza(hora_actual) if tipo == "INGRESO" else 0
    
    nueva_fila = {
        "DNI": dni, "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
        "Hora": hora_actual, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza
    }
    df = pd.read_csv(ARCHIVO_MARCACIONES)
    pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True).to_csv(ARCHIVO_MARCACIONES, index=False)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Sr. Lobo BPO", layout="centered")
inicializar_sistema()
df_empleados = pd.read_csv(ARCHIVO_EMPLEADOS)

# BARRA LATERAL PROTEGIDA
st.sidebar.title("🐺 Gestión")
acceso_admin = st.sidebar.checkbox("Acceso Administrador")
modo = "Marcación"

if acceso_admin:
    password = st.sidebar.text_input("Contraseña:", type="password")
    if password == "Lobo2026":
        modo = st.sidebar.radio("Módulo:", ["Marcación", "Reporte Nómina"])
    elif password != "":
        st.sidebar.error("Clave incorrecta")

if modo == "Marcación":
    col1, col2 = st.columns([1.5, 4])
    with col1:
        if os.path.exists(LOGO_NOMBRE): st.image(LOGO_NOMBRE, width=180)
        else: st.write("🐺")
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1E3A8A; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
    st.divider()

    # SCRIPT DE FOCO INTELIGENTE MEJORADO
    components.html("""<script>function setFocus(){ var ins = window.parent.document.querySelectorAll('input[type="text"]'); if(ins.length===1){ins[0].focus();}else if(ins.length>1){ins[1].focus();}} setInterval(setFocus, 500);</script>""", height=0)

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_{st.session_state.reset_key}")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.success(f"👤 Bienvenido: {nombre}")
            c1, c2 = st.columns(2); c3, c4 = st.columns(2)
            
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, type="primary"):
                    registrar(dni, nombre, "INGRESO"); st.session_state.reset_key += 1; st.rerun()
            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True):
                    st.session_state.mostrando_obs = True; st.rerun()
            if st.session_state.mostrando_obs:
                motivo = st.text_input("MOTIVO DEL PERMISO:", key=f"mot_{st.session_state.reset_key}")
                if motivo:
                    registrar(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                    st.session_state.mostrando_obs = False; st.session_state.reset_key += 1; st.rerun()
            with c4:
                if st.button("🔙 RETORNO PERMISO", use_container_width=True):
                    registrar(dni, nombre, "RETORNO_PERMISO"); st.session_state.reset_key += 1; st.rerun()
            with c2:
                if st.button("📤 SALIDA FINAL", use_container_width=True):
                    registrar(dni, nombre, "SALIDA"); st.session_state.reset_key += 1; st.rerun()
        else:
            st.error("DNI no registrado"); time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Reporte Nómina":
    st.header("💰 Reporte de Nómina y Tardanzas")
    df_m = pd.read_csv(ARCHIVO_MARCACIONES)
    df_reporte = df_m.merge(df_empleados, on="DNI", how="left")
    
    # Cálculo de descuento: (Sueldo / 30 dias / 8 horas / 60 min) * Minutos
    df_reporte['Descuento_Soles'] = (df_reporte['Salario'] / 30 / 8 / 60) * df_reporte['Tardanza_Min']
    df_reporte['Descuento_Soles'] = df_reporte['Descuento_Soles'].round(2)

    st.write(f"Nota: Se aplica una tolerancia de {MINUTOS_TOLERANCIA} minutos sobre las {HORA_ENTRADA_OFICIAL}.")
    st.dataframe(df_reporte[['Fecha', 'Nombre_x', 'Hora', 'Tipo', 'Tardanza_Min', 'Descuento_Soles', 'Observacion']], use_container_width=True)
    
    csv = df_reporte.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Reporte de Descuentos", data=csv, file_name="Reporte_Final_Lobo.csv", mime='text/csv', use_container_width=True)
