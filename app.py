import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import time 
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Asistencia Lobo", layout="wide")
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MENSUAL = 30 

# --- ESTILOS CSS ---
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
    }
    [data-testid="stSidebar"] .stImage {
        margin-bottom: -15px;
    }
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# OPTIMIZACIÓN DE ARRANQUE: Caché de conexión
@st.cache_resource(ttl=600)
def obtener_conexion():
    return st.connection("gsheets", type=GSheetsConnection)

def registrar_en_nube(nombre, dni, tipo, salario, obs=""):
    try:
        ahora = obtener_hora_peru()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        
        tardanza_hoy = 0
        descuento_hoy = 0
        if tipo == "INGRESO":
            h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if ahora.time() > h_oficial:
                diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
                tardanza_hoy = int(diff.total_seconds() / 60)
                costo_min = (salario / 30 / 8 / 60)
                descuento_hoy = round(tardanza_hoy * costo_min, 2)

        nueva_fila = pd.DataFrame([{
            "Fecha": fecha_str, "DNI": str(dni).strip(), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza_hoy,
            "Descuento_Soles": descuento_hoy, "Observacion": obs
        }])
        
        conn = obtener_conexion()
        url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_hist, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_hoja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.2)
        if "p_m" in st.session_state: st.session_state.p_m = False
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error técnico: {e}")

# --- 3. CONEXIÓN Y FOCO ---
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

components.html("""
    <script>
    const f = () => {
        const i = window.parent.document.querySelectorAll('input[type="text"]');
        if (i.length > 0) {
            const active = window.parent.document.activeElement;
            if (active.tagName !== 'INPUT' && active.tagName !== 'TEXTAREA') { i[0].focus(); }
        }
    };
    setInterval(f, 2000);
    </script>
""", height=0)

# --- 4. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    col_logo, col_text = st.columns([0.3, 0.7])
    with col_logo:
        if os.path.exists("Lobo.png"): st.image("Lobo.png", width=50)
    with col_text:
        st.markdown("<h3 style='margin-top: 10px; color: #1E3A8A;'>Gestión Lobo</h3>", unsafe_allow_html=True)
    
    st.divider()
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026": modo = "Admin"

# --- 5. CABECERA PRINCIPAL ---
c_logo, c_tit = st.columns([1, 2.5])
with c_logo:
    if os.path.exists("logo_lobo.png"): st.image("logo_lobo.png", width=300)
with c_tit:
    st.markdown("<h1 style='color: #1E3A8A;'>Marcación Sr. Lobo</h1>", unsafe_allow_html=True)

st.divider()

if modo == "Marcación":
    st.write("### DIGITE SU DNI:")
    c_dni_box, _ = st.columns([0.15, 0.85]) 
    with c_dni_box:
        dni_in = st.text_input("DNI", key=f"dni_{st.session_state.reset_key}", label_visibility="collapsed", max_chars=12)

    if dni_in:
        df_emp = pd.read_csv("empleados.csv", dtype={'DNI': str})
        dni_l = str(dni_in).strip()
        emp = df_emp[df_emp['DNI'] == dni_l]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            salario_v = float(emp.iloc[0]['Salario'])
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            conn = obtener_conexion()
            url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
            df_hist_check = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            df_hist_check['DNI'] = df_hist_check['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            marcas_hoy = df_hist_check[(df_hist_check['DNI'] == dni_l) & (df_hist_check['Fecha'] == hoy)]
            
            ya_i = "INGRESO" in marcas_hoy['Tipo'].values
            ya_s = "SALIDA" in marcas_hoy['Tipo'].values
            en_p = (not marcas_hoy.empty and marcas_hoy.iloc[-1]['Tipo'] == "SALIDA PERMISO")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, disabled=ya_i): 
                    registrar_en_nube(nombre, dni_l, "INGRESO", salario_v)
            with c2:
                if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_i or ya_s or en_p)): 
                    registrar_en_nube(nombre, dni_l, "SALIDA", salario_v)
            
            c3, c4 = st.columns(2)
            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_i or ya_s or en_p)): 
                    st.session_state.p_m = True
            with c4:
                if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_p)): 
                    registrar_en_nube(nombre, dni_l, "ENTRADA PERMISO", salario_v)

            if st.session_state.get("p_m", False):
                st.markdown("---")
                motivo = st.text_input("Indique el motivo del permiso:", key="mot_p")
                if st.button("CONFIRMAR"):
                    if motivo: registrar_en_nube(nombre, dni_l, "SALIDA PERMISO", salario_v, motivo)
                    else: st.error("Escriba un motivo.")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN ---
    st.header("📊 Reporte de Asistencia Lobo")
    conn = obtener_conexion()
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        df_h['Fecha_dt'] = pd.to_datetime(df_h['Fecha'])
        df_h['Año'] = df_h['Fecha_dt'].dt.year
        df_h['Mes'] = df_h['Fecha_dt'].dt.month
        
        c_a, c_m, c_u = st.columns(3)
        with c_a: f_anio = st.selectbox("Año:", sorted(df_h['Año'].unique(), reverse=True))
        with c_m: f_mes = st.selectbox("Mes:", range(1, 13), index=obtener_hora_peru().month-1)
        with c_u: f_usu = st.multiselect("Usuario:", options=df_h['Nombre'].unique())
        
        df_f = df_h[(df_h['Año'] == f_anio) & (df_h['Mes'] == f_mes)]
        if f_usu: df_f = df_f[df_f['Nombre'].isin(f_usu)]

        st.dataframe(df_f.drop(columns=['Año', 'Mes', 'Fecha_dt']), use_container_width=True)

        st.divider()
        t_min = df_f['Tardanza_Min'].sum()
        t_sol = df_f['Descuento_Soles'].sum()
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Minutos de Tardanza", f"{t_min} min")
        c_m2.metric("Descuento Acumulado", f"S/. {t_sol:.2f}")
        m_final = max(0, (t_min - TOLERANCIA_MENSUAL) * (t_sol / (t_min if t_min > 0 else 1)))
        c_m3.metric("Monto Final (Tolerancia 30m)", f"S/. {round(m_final, 2)}")
    else: st.info("Sin registros.")
