import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time  # Crucial para evitar el NameError
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
COSTO_MINUTO = 0.15  
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MENSUAL = 30 

# --- ESTILOS CSS: RESTAURACIÓN VISUAL TOTAL ---
st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
        url("https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1350&q=80");
        background-size: cover; background-attachment: fixed;
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.94);
        padding: 3rem; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        position: relative;
    }
    /* Gota de agua sutil restaurada */
    .main .block-container::before {
        content: ""; position: absolute; top: 50%; left: 50%; width: 500px; height: 500px;
        background-image: url("https://raw.githubusercontent.com/Yovanni/asistencia/main/Lobo.png");
        background-repeat: no-repeat; background-position: center; background-size: contain;
        opacity: 0.05; transform: translate(-50%, -50%); pointer-events: none; z-index: 0;
    }
    /* Limpieza de logos impecable */
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    .sidebar-brand-horizontal { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA Y REGISTRO ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo):
    try:
        ahora = obtener_hora_peru()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        
        tardanza = 0
        if tipo == "INGRESO":
            h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if ahora.time() > h_oficial:
                diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
                tardanza = int(diff.total_seconds() / 60)

        nueva_fila = pd.DataFrame([{
            "Fecha": fecha_str, "DNI": str(dni), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza
        }])
        
        df_actual = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO: {nombre}")
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# --- 3. CONEXIÓN Y ESTADO ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 4. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    st.markdown("<div class='sidebar-brand-horizontal'>", unsafe_allow_html=True)
    c_s_logo, c_s_text = st.columns([0.35, 0.65])
    with c_s_logo:
        if os.path.exists("Lobo.png"): st.image("Lobo.png", width=55) #
    with c_s_text:
        st.markdown("<h2 style='color: #1E3A8A; font-size: 21px; margin: 0; padding-top: 15px;'>Gestión Lobo</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        clave = st.text_input("Contraseña:", type="password")
        if clave == "Lobo2026": modo = "Admin"

# --- FOCO INTELIGENTE ---
if not acceso_admin:
    components.html(f"""<script>
        const f = () => {{
            const i = window.parent.document.querySelectorAll('input[type="text"]');
            if (i.length > 0 && window.parent.document.activeElement !== i[0]) i[0].focus();
        }};
        setInterval(f, 1000);
    </script>""", height=0)

# --- 5. CABECERA PRINCIPAL ---
c_izq, c_logo_p, c_tit, c_der = st.columns([0.5, 3.5, 6, 0.5])
with c_logo_p:
    if os.path.exists("logo_lobo.png"):
        st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True) #
        st.image("logo_lobo.png", width=320)
        st.markdown("</div>", unsafe_allow_html=True)
with c_tit:
    st.markdown("<div style='padding-top: 15px;'><h1 style='color: #1E3A8A; font-size: 50px; margin-bottom: 0px;'>Marcación Sr. Lobo</h1><h2 style='color: #444; font-size: 26px; margin-top: -10px;'>Sr. Lobo BPO Solutions</h2></div>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni, _ = st.columns([1, 4])
    with c_dni:
        dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        emp = df_emp[df_emp['DNI'] == str(dni_in).strip()]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            # --- LÓGICA DE BLOQUEO RESTAURADA ---
            df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            marcas_hoy = df_hist[(df_hist['DNI'] == str(dni_in)) & (df_hist['Fecha'] == hoy)]
            
            ya_ingreso = "INGRESO" in marcas_hoy['Tipo'].values
            ya_salio = "SALIDA" in marcas_hoy['Tipo'].values
            en_permiso = (not marcas_hoy.empty and marcas_hoy.iloc[-1]['Tipo'] == "SALIDA PERMISO")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, disabled=ya_ingreso):
                    registrar_en_nube(nombre, dni_in, "INGRESO")
            with c2:
                if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_in, "SALIDA")
            
            c3, c4 = st.columns(2)
            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_in, "SALIDA PERMISO")
            with c4:
                if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_permiso)):
                    registrar_en_nube(nombre, dni_in, "ENTRADA PERMISO")
            
            if ya_salio: st.warning("Jornada finalizada por hoy.")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN: 100% RESTAURADO ---
    st.header("📋 Reporte Auditado de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'], errors='coerce')
        meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
        
        f1, f2, f3 = st.columns(3)
        with f1: sel_anio = st.selectbox("Año", sorted(df_h['Fecha_dt'].dt.year.unique(), reverse=True))
        with f2:
            m_num = sorted(df_h[df_h['Fecha_dt'].dt.year == sel_anio]['Fecha_dt'].dt.month.unique())
            sel_mes = st.selectbox("Mes", m_num, format_func=lambda x: meses_dict[x])
        with f3:
            nombres = sorted(df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)]['Nombre'].unique())
            sel_nombre = st.selectbox("Trabajador", ["TODOS"] + nombres)
        
        df_f = df_h[(df_h['Fecha_dt'].dt.year == sel_anio) & (df_h['Fecha_dt'].dt.month == sel_mes)].copy()
        if sel_nombre != "TODOS": df_f = df_f[df_f['Nombre'] == sel_nombre]

        st.dataframe(df_f.drop(columns=['Fecha_dt']), use_container_width=True) #
        
        st.subheader("💰 Resumen de Auditoría")
        resumen = df_f.groupby('Nombre')['Tardanza_Min'].sum().reset_index()
        resumen['Excedente'] = resumen['Tardanza_Min'].apply(lambda x: (x - TOLERANCIA_MENSUAL) if x > TOLERANCIA_MENSUAL else 0)
        resumen['Descuento_Soles'] = resumen['Excedente'] * COSTO_MINUTO
        
        st.table(resumen)
        st.metric("Total General", f"S/ {resumen['Descuento_Soles'].sum():.2f}")
