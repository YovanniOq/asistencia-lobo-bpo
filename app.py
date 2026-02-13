import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
COSTO_MINUTO = 0.15  
HORA_ENTRADA_OFICIAL = "08:00:00" 

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco automático inteligente
components.html("""
    <script>
    const forceFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        const passInputs = window.parent.document.querySelectorAll('input[type="password"]');
        if (inputs.length > 0) {
            const dniInput = inputs[0];
            const activeElem = window.parent.document.activeElement;
            const escribiendoObservacion = inputs.length > 1;
            let focusingOnPassword = false;
            passInputs.forEach(p => { if(activeElem === p) focusingOnPassword = true; });
            if (activeElem !== dniInput && !focusingOnPassword && !escribiendoObservacion) {
                dniInput.focus();
            }
        }
    };
    setInterval(forceFocus, 1000);
    </script>
""", height=0)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]

if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "mostrar_obs" not in st.session_state: st.session_state.mostrar_obs = False

# --- 3. FUNCIÓN DE GRABACIÓN ---
def registrar_en_nube(dni, nombre, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        tardanza_min = 0
        descuento = 0
        if tipo == "INGRESO":
            hora_actual = ahora.time()
            hora_limite = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if hora_actual > hora_limite:
                diff = datetime.combine(datetime.today(), hora_actual) - datetime.combine(datetime.today(), hora_limite)
                tardanza_min = int(diff.total_seconds() / 60)
                descuento = round(tardanza_min * COSTO_MINUTO, 2)

        nueva_fila = pd.DataFrame([{
            "DNI": str(dni), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, 
            "Tardanza_Min": tardanza_min, "Descuento_Soles": descuento
        }])
        
        # Lectura sin caché para asegurar que escribimos sobre lo último
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_h, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        st.error(f"Error al grabar: {e}")

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
    c_in, _ = st.columns([1, 4])
    with c_in:
        dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed")
    
    if dni_in:
        try:
            df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
            emp = df_emp[df_emp['DNI'] == str(dni_in)]
            
            if not emp.empty:
                nombre = emp.iloc[0]['Nombre']
                st.info(f"👤 TRABAJADOR: {nombre}")
                
                # --- CONSULTA OBLIGATORIA AL DRIVE (Sincronización Real) ---
                # ttl=0 obliga a la App a ignorar su memoria interna y mirar el Excel
                df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
                hoy = obtener_hora_peru().strftime("%Y-%m-%d")
                
                # Convertimos DNI a string en la búsqueda para evitar errores de tipo
                df_h['DNI'] = df_h['DNI'].astype(str)
                regs_hoy = df_h[(df_h['DNI'] == str(dni_in)) & (df_h['Fecha'] == hoy)]
                
                # Determinamos el estado basado en el último registro encontrado
                u_tipo = regs_hoy.iloc[-1]['Tipo'] if not regs_hoy.empty else "NADA"

                # DIBUJAR BOTONES SEGÚN LA NUBE
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    # INGRESO: Se bloquea si u_tipo ya NO es "NADA"
                    if st.button("📥 INGRESO", use_container_width=True, disabled=(u_tipo != "NADA")):
                        registrar_en_nube(dni_in, nombre, "INGRESO")
                
                with c2:
                    # PERMISO: Solo si está "dentro"
                    esta_dentro = (u_tipo in ["INGRESO", "RETORNO_PERMISO"])
                    if st.button("🚶 PERMISO", use_container_width=True, disabled=not esta_dentro):
                        st.session_state.mostrar_obs = True
                        st.rerun()
                
                with c3:
                    # RETORNO: Solo si está en permiso
                    if st.button("🔙 RETORNO", use_container_width=True, disabled=(u_tipo != "SALIDA_PERMISO")):
                        registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
                
                with c4:
                    # SALIDA: Solo si está dentro
                    if st.button("📤 SALIDA", use_container_width=True, disabled=not esta_dentro):
                        registrar_en_nube(dni_in, nombre, "SALIDA")

                if u_tipo == "SALIDA":
                    st.warning("⚠️ Turno Finalizado por hoy.")

                if st.session_state.mostrar_obs:
                    st.divider()
                    motivo = st.text_input("MOTIVO DEL PERMISO:")
                    if motivo: 
                        registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
            else:
                st.error("DNI no registrado.")
        except Exception as e:
            st.error(f"Error al verificar estado: {e}")
else:
    # MODULO ADMIN
    st.header("📋 Reporte Lobo")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    st.dataframe(df_h, use_container_width=True)
