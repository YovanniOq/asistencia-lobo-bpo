import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
LOGO_ARCHIVO = "logo_lobo.png"
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# --- 2. CONFIGURACIÓN DE PÁGINA Y FOCO ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# Script de foco automático para agilizar la fila
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

# --- 3. CONEXIÓN Y ESTADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

# Inicializar llaves de refresco
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "pedir_obs" not in st.session_state: st.session_state.pedir_obs = False

# --- 4. FUNCIÓN DE GUARDADO MAESTRA ---
def registrar_movimiento(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, "Tardanza_Min": 0
        }])
        
        # Leer y actualizar inmediatamente
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO: {nombre}")
        st.balloons()
        time.sleep(1.5)
        
        # LIMPIEZA TOTAL PARA EL SIGUIENTE
        st.session_state.reset_key += 1
        st.session_state.pedir_obs = False
        st.rerun()
    except Exception as e:
        if "200" in str(e): # Bypass para el falso error de Google
            st.success(f"✅ REGISTRO EXITOSO")
            time.sleep(1.5)
            st.session_state.reset_key += 1
            st.session_state.pedir_obs = False
            st.rerun()
        else:
            st.error(f"Error al guardar: {e}")

# --- 5. INTERFAZ VISUAL ---
with st.sidebar:
    st.title("🐺 Panel Admin")
    modo = "Marcación"
    if st.checkbox("Acceso Administrador"):
        if st.text_input("Clave:", type="password") == "Lobo2026":
            modo = st.radio("Módulo:", ["Marcación", "Historial"])

col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_ARCHIVO): st.image(LOGO_ARCHIVO, width=180)
with col_titulo:
    st.markdown("<h1 style='color: #1E3A8A; margin-top: 15px;'>SR. LOBO BPO SOLUTIONS</h1>", unsafe_allow_html=True)
    st.write(f"🕒 {obtener_hora_peru().strftime('%H:%M:%S')}")

st.divider()

# --- 6. LÓGICA DE NEGOCIO (EL CORAZÓN DEL PROGRAMA) ---
if modo == "Marcación":
    st.write("### DIGITE SU DNI Y PRESIONE ENTER:")
    c_dni, _ = st.columns([1, 3])
    with c_dni:
        dni = st.text_input("", key=f"input_{st.session_state.reset_key}", label_visibility="collapsed")

    if dni:
        try:
            df_emp = pd.read_csv("empleados.csv")
            emp = df_emp[df_emp['DNI'].astype(str) == str(dni)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                # REVISAR EL PASADO DEL TRABAJADOR HOY
                df_cloud = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                marcs_hoy = df_cloud[(df_cloud['DNI'].astype(str) == str(dni)) & (df_cloud['Fecha'] == hoy)]
                
                # Estados lógicos
                ya_ingreso = not marcs_hoy[marcs_hoy['Tipo'] == "INGRESO"].empty
                ultimo_estado = marcs_hoy.iloc[-1]['Tipo'] if not marcs_hoy.empty else "NADA"
                ya_salio_final = not marcs_hoy[marcs_hoy['Tipo'] == "SALIDA"].empty

                if ya_salio_final:
                    st.warning("🚫 Ya marcaste tu salida final por hoy.")
                else:
                    # DIBUJAR BOTONES SEGÚN EL ESTADO
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1: # INGRESO: Solo si no ha entrado hoy
                        if st.button("📥 INGRESO", disabled=ya_ingreso, use_container_width=True):
                            registrar_movimiento(dni, nombre, "INGRESO")
                    
                    with col2: # PERMISO: Solo si ya ingresó y no está de permiso ahora
                        if st.button("🚶 PERMISO", disabled=(not ya_ingreso or ultimo_estado == "SALIDA_PERMISO"), use_container_width=True):
                            st.session_state.pedir_obs = True
                    
                    with col3: # RETORNO: Solo si su último estado fue irse de permiso
                        if st.button("🔙 RETORNO", disabled=(ultimo_estado != "SALIDA_PERMISO"), use_container_width=True):
                            registrar_movimiento(dni, nombre, "RETORNO_PERMISO")
                    
                    with col4: # SALIDA: Solo si ya ingresó
                        if st.button("📤 SALIDA", disabled=not ya_ingreso, use_container_width=True):
                            registrar_movimiento(dni, nombre, "SALIDA")

                    # CAJA DE OBSERVACIONES (SOLO PARA PERMISO)
                    if st.session_state.pedir_obs:
                        st.divider()
                        motivo = st.text_input("Escriba el motivo del permiso y presione ENTER:")
                        if motivo:
                            registrar_movimiento(dni, nombre, "SALIDA_PERMISO", obs=motivo)
            else:
                st.error("DNI no encontrado.")
        except Exception as e:
            st.error(f"Error de sistema: {e}")

elif modo == "Historial":
    st.header("📋 Reporte del Día")
    st.dataframe(conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0), use_container_width=True)
