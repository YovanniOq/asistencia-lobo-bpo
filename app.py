import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")

# PARÁMETROS MONETARIOS
COSTO_MINUTO = 0.15  
HORA_ENTRADA_OFICIAL = "08:00:00" 

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Foco automático
components.html("<script>setInterval(function(){var inputs = window.parent.document.querySelectorAll('input'); if(inputs.length > 0 && window.parent.document.activeElement.tagName !== 'INPUT') inputs[0].focus();}, 500);</script>", height=0)

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
        
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.session_state.ultimo_estado[str(dni)] = tipo
        st.success(f"✅ {tipo} REGISTRADO | S/ {descuento}")
        time.sleep(1.2)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

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
                        motivo = st.text_input("MOTIVO DEL PERMISO:")
                        if motivo: registrar_en_nube(dni_in, nombre, "SALIDA_PERMISO", obs=motivo)
            else: st.error("DNI no registrado.")
        except: st.error("Error base local.")

else: # --- REPORTE BLINDADO CONTRA COLUMNAS FALTANTES ---
    st.header("📋 Reporte Mensual Lobo")
    try:
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        if not df_h.empty:
            # ASEGURAR QUE EXISTAN LAS COLUMNAS NUEVAS PARA EVITAR EL ERROR ROJO
            if 'Descuento_Soles' not in df_h.columns:
                df_h['Descuento_Soles'] = 0.0
            if 'Tardanza_Min' not in df_h.columns:
                df_h['Tardanza_Min'] = 0
            
            # Limpiar datos para el filtro
            df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
            df_h = df_h.dropna(subset=['Fecha_dt'])
            
            f1, f2, _ = st.columns([1, 1, 2])
            with f1:
                anios = sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True)
                sel_anio = st.selectbox("Año", anios if anios else [2026])
            with f2:
                meses_disp = sorted(df_h[df_h['Fecha_dt'].dt.year == sel_anio]['Fecha_dt'].dt.month.unique())
                sel_mes = st.selectbox("Mes", meses_disp if meses_disp else [2])
            
            df_filtrado = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]
            df_mostrar = df_filtrado.drop(columns=['Fecha_dt'])
            
            st.dataframe(df_mostrar, use_container_width=True)
            
            # Cálculo seguro del total
            total_money = pd.to_numeric(df_mostrar['Descuento_Soles'], errors='coerce').sum()
            st.metric("Total Descuentos (Mes Seleccionado)", f"S/ {total_money:.2f}")
            
            csv = df_mostrar.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", csv, "Reporte_Asistencia.csv", "text/csv")
        else:
            st.info("No hay registros en el
