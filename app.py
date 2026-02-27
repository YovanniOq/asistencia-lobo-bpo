import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time
import base64
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
COSTO_MINUTO = 0.15  
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MENSUAL = 30 #

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Función infalible para convertir imagen local a Base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# --- JAVASCRIPT DE FOCO INTELIGENTE ---
components.html("""
    <script>
    const forceFocus = () => {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        const passInputs = window.parent.document.querySelectorAll('input[type="password"]');
        if (inputs.length > 0) {
            const dniInput = inputs[0];
            const activeElem = window.parent.document.activeElement;
            let escribiendoPass = false;
            passInputs.forEach(p => { if(activeElem === p) escribiendoPass = true; });
            const escribiendoObs = inputs.length > 1 && activeElem === inputs[1];
            if (activeElem !== dniInput && !escribiendoPass && !escribiendoObs) {
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
        if tipo == "INGRESO":
            hora_act = ahora.time()
            hora_lim = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if hora_act > hora_lim:
                diff = datetime.combine(datetime.today(), hora_act) - datetime.combine(datetime.today(), hora_lim)
                tardanza_min = int(diff.total_seconds() / 60)

        nueva_fila = pd.DataFrame([{
            "DNI": str(dni).strip(), "Nombre": nombre, "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M:%S"), "Tipo": tipo, "Observacion": obs, 
            "Tardanza_Min": tardanza_min
        }])
        
        st.cache_data.clear()
        df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_h, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.2)
        st.session_state.reset_key += 1
        st.session_state.mostrar_obs = False
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 4. INTERFAZ ---
modo = "Marcación"
with st.sidebar:
    # --- SOLO EL LOBO CENTRADO ARRIBA DEL TEXTO ---
    if os.path.exists("logo_lobo.png"):
        img_64 = get_base64_image("logo_lobo.png")
        st.markdown(f"""
            <div style='text-align: center; margin-bottom: 10px;'>
                <div style='width: 80px; height: 80px; overflow: hidden; margin: 0 auto;'>
                    <img src='data:image/png;base64,{img_64}' 
                         style='width: 380px; margin-left: -5px; margin-top: -10px;'>
                </div>
                <h2 style='color: #1E3A8A; margin-top: 10px; font-size: 24px;'>Gestión Lobo</h2>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.title("Gestión Lobo")
    
    st.write("---")
    if st.checkbox("Acceso Administrador"):
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026":
            modo = "Admin"

# Cabecera principal centrada
c_izq, c_logo, c_tit, c_der = st.columns([1, 3, 6, 1])
with c_logo:
    if os.path.exists("logo_lobo.png"):
        st.write(""); st.write("")
        st.image("logo_lobo.png", width=300)
with c_tit:
    st.markdown(f"""
        <div style='padding-top: 15px;'>
            <h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>Marcación Sr. Lobo</h1>
            <h3 style='color: #444; font-size: 26px; margin-top: -10px;'>Sr. Lobo BPO Solutions</h3>
        </div>
    """, unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 4])
    with c_dni:
        dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        st.cache_data.clear()
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            df_h['DNI'] = df_h['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            regs = df_h[(df_h['DNI'] == str(dni_in).strip()) & (df_h['Fecha'] == hoy)]
            u_tipo = str(regs.iloc[-1]['Tipo']).strip().upper() if not regs.empty else "NADA"

            col_btn = st.columns(4)
            with col_btn[0]:
                if st.button("📥 INGRESO", use_container_width=True, disabled=(u_tipo != "NADA")):
                    registrar_en_nube(dni_in, nombre, "INGRESO")
            with col_btn[1]:
                esta_dentro = (u_tipo in ["INGRESO", "RETORNO_PERMISO"])
                if st.button("🚶 PERMISO", use_container_width=True, disabled=not esta_dentro):
                    st.session_state.mostrar_obs = True
                    st.rerun()
            with col_btn[2]:
                if st.button("🔙 RETORNO", use_container_width=True, disabled=(u_tipo != "SALIDA_PERMISO")):
                    registrar_en_nube(dni_in, nombre, "RETORNO_PERMISO")
            with col_btn[3]:
                if st.button("📤 SALIDA", use_container_width=True, disabled=not esta_dentro):
                    registrar_en_nube(dni_in, nombre, "SALIDA")

            if st.session_state.mostrar_obs:
                st.divider()
                motivo = st.text_input("MOTIVO DEL PERMISO (ENTER):")
                if motivo: registrar_en_nube(dni_in, nombre, "SALIDA_PER_MISO", obs=motivo)
        else:
            st.error("DNI no registrado.")

else: # --- ADMIN ---
    st.header("📋 Reporte Final Lobo")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            sel_anio = st.selectbox("Año", sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True))
        with f2:
            m_disp = sorted(df_h[df_h['Fecha_dt'].dt.year == sel_anio]['Fecha_dt'].dt.month.unique())
            sel_mes = st.selectbox("Mes", m_disp, format_func=lambda x: meses_dict[x])
        with f3:
            nombres = sorted(df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]['Nombre'].unique())
            sel_nombre = st.selectbox("Trabajador", ["TODOS"] + nombres)
        
        df_mes = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)].copy()

        resumen_mensual = df_mes.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen_mensual['Excedente_Min'] = resumen_mensual['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen_mensual['Descuento_Soles'] = resumen_mensual['Excedente_Min'] * COSTO_MINUTO

        df_final = df_mes.merge(resumen_mensual[['Nombre', 'Descuento_Soles']], on='Nombre', how='left')

        if sel_nombre != "TODOS":
            df_final = df_final[df_final['Nombre'] == sel_nombre]
            resumen_mensual = resumen_mensual[resumen_mensual['Nombre'] == sel_nombre]

        st.subheader("Historial de Marcaciones")
        st.dataframe(df_final.drop(columns=['Fecha_dt']), use_container_width=True)
        
        st.subheader("💰 Auditoría de Planilla (Bolsa 30 min)")
        st.table(resumen_mensual)

        total_final = resumen_mensual['Descuento_Soles'].sum()
        st.metric("Total General a Descontar", f"S/ {total_final:.2f}")
        
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Reporte Auditado", csv, f"Auditoria_Lobo_{meses_dict[sel_mes]}.csv", "text/csv")
