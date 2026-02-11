import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
ARCHIVO_MARCACIONES = "marcacion.csv"
ARCHIVO_EMPLEADOS = "empleados.csv"
# Asegúrate de que en GitHub el archivo se llame exactamente: logo_lobo.png
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
st.set_page_config(page_title="Sr. Lobo BPO - Asistencia", layout="centered")
inicializar_sistema()
df_empleados = pd.read_csv(ARCHIVO_EMPLEADOS)

# BARRA LATERAL PRIVADA (A pedido de Ascar)
st.sidebar.title("🐺 Gestión")
acceso_admin = st.sidebar.checkbox("Acceso Administrador")

if acceso_admin:
    password = st.sidebar.text_input("Contraseña:", type="password")
    if password == "Lobo2026": # Esta es tu clave privada
        modo = st.sidebar.radio("Módulo:", ["Marcación", "Reporte Nómina"])
    else:
        st.sidebar.warning("Clave requerida")
        modo = "Marcación"
else:
    modo = "Marcación"

if modo == "Marcación":
    # --- DISEÑO DEL ENCABEZADO (Lobo izquierda, Letras centro) ---
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # Lógica flexible para encontrar el logo en el servidor
        if os.path.exists(LOGO_NOMBRE):
            st.image(LOGO_NOMBRE, width=120)
        else:
            st.markdown("### 🐺") # Muestra un lobo genérico si no encuentra la imagen
            st.caption("Subir logo_lobo.png a GitHub")
            
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1E3A8A; margin-top: 10px; font-family: Arial;'>SR. LOBO BPO SOLUTIONS SAC</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-weight: bold;'>CONTROL DE ASISTENCIA</p>", unsafe_allow_html=True)
    
    st.divider()

    if "reset_key" not in st.session_state: st.session_state.reset_key = 0
    if "mostrando_obs" not in st.session_state: st.session_state.mostrando_obs = False

    # --- SCRIPT DE FOCO AUTOMÁTICO REFORZADO ---
    components.html(
        f"""
        <script>
            function setFocus() {{
                const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                if (inputs.length > 0) {{
                    inputs[0].focus();
                }}
            }}
            setTimeout(setFocus, 500);
            setTimeout(setFocus, 1500);
        </script>
        """,
        height=0,
    )

    dni = st.text_input("DIGITE SU DNI Y PRESIONE ENTER:", key=f"dni_input_{st.session_state.reset_key}")

    if dni:
        emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            ult = obtener_ultimo_registro(dni)
            est = ult['Tipo'] if ult is not None else "SIN MARCAR"
            
            if est == "SALIDA":
                st.warning(f"Jornada terminada para: {nombre}")
                time.sleep(2); st.session_state.reset_key += 1; st.rerun()
            else:
                st.info(f"👤 {nombre} | Estado: {est}")
                c1, c2 = st.columns(2); c3, c4 = st.columns(2)
                
                with c1:
                    if st.button("📥 INGRESO", use_container_width=True, type="primary", disabled=(est != "SIN MARCAR")):
                        registrar(dni, nombre, "INGRESO")
                        st.session_state.reset_key += 1; st.rerun()
                with c3:
                    if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(est != "INGRESO")):
                        st.session_state.mostrando_obs = True
                
                if st.session_state.mostrando_obs:
                    motivo = st.text_input("MOTIVO DEL PERMISO (Enter):", key=f"obs_box_{st.session_state.reset_key}")
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
            st.error("DNI no registrado."); time.sleep(1); st.session_state.reset_key += 1; st.rerun()

elif modo == "Reporte Nómina":
    st.header("💰 Historial de Marcaciones")
    df_m = pd.read_csv(ARCHIVO_MARCACIONES)
    st.dataframe(df_m, use_container_width=True)
