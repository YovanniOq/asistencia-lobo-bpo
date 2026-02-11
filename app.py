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

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

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
    hora_str = ahora.strftime("%H:%M:%S")
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_str, '%H:%M:%S')
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, '%H:%M:%S')
        if t_marcada > t_oficial:
            dif = int((t_marcada - t_oficial).total_seconds() / 60)
            if dif > MINUTOS_TOLERANCIA: tardanza = dif

    nueva_fila = {
        "DNI": dni, "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
        "Hora": hora_str, "Tipo": tipo, "Observacion": obs, "Tardanza_Min": tardanza
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
        modo = st.sidebar.radio("Módulo:", ["Marcación", "Historial Mensual"])

if modo == "Marcación":
    col1, col2 = st.columns([1.5, 4])
    with col1:
        if os.path.exists(LOGO_NOMBRE): st.image(LOGO_NOMBRE, width=180)
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
    st.divider()

    # FOCO INTELIGENTE (Prioriza motivo si está abierto, sino DNI)
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
                st.warning(f"🚫 {nombre}, ya registraste tu salida final hoy.")
                time.sleep(2); st.session_state.reset_key += 1; st.rerun()
            else:
                st.success(f"👤 {nombre} | Estado: {est}")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("📥 INGRESO", disabled=(est != "SIN MARCAR")):
                        registrar(dni, nombre, "INGRESO"); st.session_state.reset_key += 1; st.rerun()
                with c2:
                    if st.button("🚶 PERMISO", disabled=(est != "INGRESO" and est != "RETORNO_PERMISO")):
                        st.session_state.mostrando_obs = True; st.rerun()
                if st.session_state.mostrando_obs:
                    motivo = st.text_input("MOTIVO:", key=f"mot_{st.session_state.reset_key}")
                    if motivo:
                        registrar(dni, nombre, "SALIDA_PERMISO", obs=motivo)
                        st.session_state.mostrando_obs = False; st.session_state.reset_key += 1; st.rerun()
                with c3:
                    if st.button("🔙 RETORNO", disabled=(est != "SALIDA_PERMISO")):
                        registrar(dni, nombre, "RETORNO_PERMISO"); st.session_state.reset_key += 1; st.rerun()
                with c4:
                    if st.button("📤 SALIDA", disabled=(est not in ["INGRESO", "RETORNO_PERMISO"])):
                        registrar(dni, nombre, "SALIDA"); st.session_state.reset_key += 1; st.rerun()
        else:
            st.error("DNI no registrado"); time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Historial Mensual":
    st.header("💰 Auditoría de Nómina")
    df_m = pd.read_csv(ARCHIVO_MARCACIONES)
    df_m['Fecha'] = pd.to_datetime(df_m['Fecha'])
    
    col_a, col_b = st.columns(2)
    mes_sel = col_a.selectbox("Mes:", range(1, 13), index=obtener_hora_peru().month - 1)
    anio_sel = col_b.selectbox("Año:", [2026, 2027], index=0)

    df_f = df_m[(df_m['Fecha'].dt.month == mes_sel) & (df_m['Fecha'].dt.year == anio_sel)]
    df_r = df_f.merge(df_empleados, on="DNI", how="left")
    df_r['Equivalente_Dinero'] = (df_r['Salario'] / 30 / 8 / 60) * df_r['Tardanza_Min']
    df_r['Equivalente_Dinero'] = df_r['Equivalente_Dinero'].round(2)

    columnas = ['Fecha', 'Nombre_x', 'Hora', 'Tipo', 'Tardanza_Min', 'Equivalente_Dinero', 'Observacion']
    st.dataframe(df_r[columnas], use_container_width=True)
    csv = df_r[columnas].to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Reporte", data=csv, file_name="Reporte_Nomina.csv", use_container_width=True)
