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
    img { background-color: transparent !important; mix-blend-mode: multiply; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE LOGICA ---
def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

def registrar_en_nube(nombre, dni, tipo, obs=""):
    try:
        ahora = obtener_hora_peru()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        
        tardanza = 0
        descuento = 0
        if tipo == "INGRESO":
            h_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S").time()
            if ahora.time() > h_oficial:
                diff = datetime.combine(ahora.date(), ahora.time()) - datetime.combine(ahora.date(), h_oficial)
                tardanza = int(diff.total_seconds() / 60)
                descuento = round(tardanza * COSTO_MINUTO, 2)

        nueva_fila = pd.DataFrame([{
            "Fecha": fecha_str, "DNI": str(dni).strip(), "Nombre": nombre,
            "Tipo": tipo, "Hora": hora_str, "Tardanza_Min": tardanza,
            "Descuento_Soles": descuento, "Observacion": obs
        }])
        
        df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
        df_final = pd.concat([df_hist, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url_ho_ja, worksheet="Sheet1", data=df_final)
        
        st.success(f"✅ {tipo} REGISTRADO")
        time.sleep(1.5)
        st.session_state.reset_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- 4. INTERFAZ LATERAL ---
modo = "Marcación"
with st.sidebar:
    if os.path.exists("Lobo.png"): st.image("Lobo.png", width=55)
    st.markdown("### Gestión Lobo")
    acceso_admin = st.checkbox("Acceso Administrador")
    if acceso_admin:
        if st.text_input("Contraseña:", type="password") == "Lobo2026": modo = "Admin"

# --- FOCO INTELIGENTE ---
components.html("""
    <script>
    const f = () => {
        const i = window.parent.document.querySelectorAll('input[type="text"]');
        if (i.length > 0) {
            if (window.parent.document.activeElement.tagName !== 'INPUT' && 
                window.parent.document.activeElement.tagName !== 'TEXTAREA') {
                i[0].focus();
            }
        }
    };
    setInterval(f, 2000);
    </script>
""", height=0)

# --- 5. CABECERA ---
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
        dni_limpio = str(dni_in).strip()
        emp = df_emp[df_emp['DNI'] == dni_limpio]
        
        if not emp.empty:
            nombre = emp.iloc[0]['Nombre']
            st.info(f"👤 TRABAJADOR: {nombre}")
            
            df_hist = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
            df_hist['DNI'] = df_hist['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            hoy = obtener_hora_peru().strftime("%Y-%m-%d")
            marcas_hoy = df_hist[(df_hist['DNI'] == dni_limpio) & (df_hist['Fecha'] == hoy)]
            
            ya_ingreso = "INGRESO" in marcas_hoy['Tipo'].values
            ya_salio = "SALIDA" in marcas_hoy['Tipo'].values
            en_permiso = (not marcas_hoy.empty and marcas_hoy.iloc[-1]['Tipo'] == "SALIDA PERMISO")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("📥 INGRESO", use_container_width=True, disabled=ya_ingreso):
                    registrar_en_nube(nombre, dni_limpio, "INGRESO")
            with c2:
                if st.button("📤 SALIDA", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    registrar_en_nube(nombre, dni_limpio, "SALIDA")
            
            c3, c4 = st.columns(2)
            with c3:
                if st.button("🚶 SALIDA PERMISO", use_container_width=True, disabled=(not ya_ingreso or ya_salio or en_permiso)):
                    st.session_state.p_motivo = True
            with c4:
                if st.button("🏠 ENTRADA PERMISO", use_container_width=True, disabled=(not en_permiso)):
                    registrar_en_nube(nombre, dni_limpio, "ENTRADA PERMISO")

            if st.session_state.get("p_motivo", False):
                st.markdown("---")
                motivo = st.text_input("Indique el motivo del permiso:", key="mot_p")
                if st.button("CONFIRMAR SALIDA PERMISO"):
                    if motivo:
                        registrar_en_nube(nombre, dni_limpio, "SALIDA PERMISO", motivo)
                        st.session_state.p_motivo = False
                    else: st.error("Escriba un motivo.")
        else: st.error("DNI no registrado.")

else: # --- PANEL ADMIN RESTAURADO CON FILTROS Y RESUMEN ---
    st.header("📊 Reporte y Resumen de Asistencia")
    df_h = conn.read(spreadsheet=url_hoja, worksheet="Sheet1", ttl=0)
    
    if not df_h.empty:
        # Filtros
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            f_nom = st.multiselect("Filtrar por Nombre:", options=df_h['Nombre'].unique())
        with c_f2:
            f_tipo = st.multiselect("Filtrar por Movimiento:", options=df_h['Tipo'].unique())
        
        df_filtrado = df_h.copy()
        if f_nom: df_filtrado = df_filtrado[df_filtrado['Nombre'].isin(f_nom)]
        if f_tipo: df_filtrado = df_filtrado[df_filtrado['Tipo'].isin(f_tipo)]

        # Resumen
        total_tardanza = df_filtrado['Tardanza_Min'].sum()
        total_descuento = df_filtrado['Descuento_Soles'].sum()
        
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("Total Minutos Tardanza", f"{total_tardanza} min")
        c_m2.metric("Total Descuento Acumulado", f"S/. {total_descuento:.2f}")

        st.divider()
        st.dataframe(df_filtrado, use_container_width=True)
    else: st.info("No hay datos registrados.")
