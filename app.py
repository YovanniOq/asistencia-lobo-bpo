import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco automático en la casilla de DNI
components.html("""
    <script>
    function setFocus(){
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') {
            inputs[0].focus();
        }
    }
    setInterval(setFocus, 500);
    </script>
""", height=0)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False
if "ultimo_estado" not in st.session_state: st.session_state.ultimo_estado = {}

# --- 3. FUNCIÓN DE GRABACIÓN ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.session_state.ultimo_estado[str(dni)] = tipo
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        if "200" in str(e):
            st.session_state.ultimo_estado[str(dni)] = tipo
            st.session_state.reset_key += 1
            st.rerun()
        else:
            st.error(f"Error de conexión: {e}")

# --- 4. INTERFAZ ---
with st.sidebar:
    st.title("🐺 Gestión Lobo")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = "Historial"

col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=150)
with col2:
    st.markdown("<h1 style='color: #1E3A8A;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    col_input, _ = st.columns([1, 4]) 
    with col_input:
        dni_in = st.text_input("", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")
    
    if dni_in:
        try:
            df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
            emp = df_emp[df_emp['DNI'] == str(dni_in)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                estado = st.session_state.ultimo_estado.get(str(dni_in), "NADA")
                
                if estado == "SALIDA":
                    st.warning("🚫 Turno finalizado hoy.")
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if st.button("📥 INGRESO", disabled=(estado != "NADA"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "INGRESO")
                    with c2:
                        if st.button("🚶 PERMISO", disabled=(estado != "INGRESO" and estado != "RETORNO_PERMISO"), use_container_width=True):
                            st.session_state.mostrar_obs = True
                            st.rerun()
                    with c3:
                        if st.button("🔙 RETORNO", disabled=(estado != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
                    with c4:
                        if st.button("📤 SALIDA", disabled=(estado == "NADA"), use_container_width=True):
                            registrar_en_nube(dni_in, nombre, "SALIDA")

                    if st.session_state.mostrar_obs:
                        st.divider()
                        motivo = st.text_input("MOTIVO DEL PERMISO (Escriba y ENTER):")
                        if motivo:
                            registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
            else:
                st.error("DNI no registrado.")
        except Exception:
            st.error("Error al leer empleados.csv")

else:
    # --- MÓDULO ADMIN PROTEGIDO ---
    st.header("📋 Reporte de Asistencia")
    try:
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        
        if not df_h.empty:
            # Limpieza de fechas para evitar errores
            df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
            df_h = df_h.dropna(subset=['Fecha_dt'])
            
            f1, f2, _ = st.columns([1, 1, 2])
            with f1:
                anios = sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True)
                sel_anio = st.selectbox("Año", anios if anios else [2026])
            with f2:
                meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                                 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
                df_anio = df_h[df_h['Fecha_dt'].dt.year == sel_anio]
                meses_disp = sorted(df_anio['Fecha_dt'].dt.month.unique())
                sel_mes = st.selectbox("Mes", meses_disp if meses_disp else [2], format_func=lambda x: meses_nombres.get(x, "N/A"))
            
            df_filtrado = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]
            df_mostrar = df_filtrado.drop(columns=['Fecha_dt'])
            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("Aún no hay registros en la base de datos.")
            
    except Exception:
        st.warning("⏳ Sincronizando datos con Google Drive...")
