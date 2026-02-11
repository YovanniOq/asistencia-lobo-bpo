import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

# --- 1. CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00" 
TOLERANCIA_MIN = 30

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# Crear conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_en_sheets(dni, nombre, tipo):
    # Leer datos actuales de la hoja
    df_existente = conn.read(ttl=0)
    
    ahora = obtener_hora_peru()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M:%S")
    
    # Calcular tardanza si es ingreso
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_actual, "%H:%M:%S")
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S")
        if t_marcada > t_oficial:
            dif = int((t_marcada - t_oficial).total_seconds() / 60)
            if dif > TOLERANCIA_MIN:
                tardanza = dif

    # Crear nueva fila
    nueva_fila = pd.DataFrame([{
        "DNI": str(dni),
        "Nombre": nombre,
        "Fecha": fecha_hoy,
        "Hora": hora_actual,
        "Tipo": tipo,
        "Observacion": "",
        "Tardanza_Min": tardanza
    }])

    # Combinar y subir a la nube
    df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
    conn.update(data=df_actualizado)
    st.success(f"✅ {tipo} registrado con éxito.")

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Sr. Lobo BPO", layout="centered")
st.title("🐺 SR. LOBO BPO SOLUTIONS SAC")

# Cargamos empleados desde el CSV que tienes en GitHub
df_empleados = pd.read_csv("empleados.csv")

dni_input = st.text_input("DIGITE SU DNI:")

if dni_input:
    # Buscar empleado
    emp = df_empleados[df_empleados['DNI'].astype(str) == str(dni_input)]
    
    if not emp.empty:
        nombre_emp = emp.iloc[0]['Nombre']
        st.info(f"👤 Empleado: {nombre_emp}")
        
        # Verificar estado de hoy para bloquear re-ingresos
        df_hoy = conn.read(ttl=0)
        hoy_str = obtener_hora_peru().strftime("%Y-%m-%d")
        marcaciones_hoy = df_hoy[(df_hoy['DNI'].astype(str) == str(dni_input)) & (df_hoy['Fecha'] == hoy_str)]
        
        ya_salio = not marcaciones_hoy[marcaciones_hoy['Tipo'] == 'SALIDA'].empty
        ya_entro = not marcaciones_hoy[marcaciones_hoy['Tipo'] == 'INGRESO'].empty

        if ya_salio:
            st.warning("🚫 Ya registraste tu salida final hoy. ¡Hasta mañana!")
        else:
            col1, col2 = st.columns(2)
            if col1.button("📥 REGISTRAR INGRESO", disabled=ya_entro, use_container_width=True):
                registrar_en_sheets(dni_input, nombre_emp, "INGRESO")
                time.sleep(2)
                st.rerun()
            
            if col2.button("📤 REGISTRAR SALIDA", disabled=not ya_entro, use_container_width=True):
                registrar_en_sheets(dni_input, nombre_emp, "SALIDA")
                time.sleep(2)
                st.rerun()
    else:
        st.error("DNI no encontrado en el sistema.")
