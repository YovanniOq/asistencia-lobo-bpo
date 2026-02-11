import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- CONFIGURACIÓN ---
HORA_ENTRADA_OFICIAL = "08:00:00"
TOLERANCIA_MIN = 30

def obtener_hora_peru():
    return datetime.now(timezone.utc) - timedelta(hours=5)

# 1. Creamos la conexión con los Secrets que guardaste
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_en_nube(dni, nombre, tipo):
    # Leemos lo que hay en la hoja actualmente
    df_actual = conn.read(ttl=0)
    
    ahora = obtener_hora_peru()
    hora_str = ahora.strftime("%H:%M:%S")
    fecha_str = ahora.strftime("%Y-%m-%d")
    
    # Calculamos tardanza
    tardanza = 0
    if tipo == "INGRESO":
        t_marcada = datetime.strptime(hora_str, "%H:%M:%S")
        t_oficial = datetime.strptime(HORA_ENTRADA_OFICIAL, "%H:%M:%S")
        if t_marcada > t_oficial:
            tardanza = max(0, int((t_marcada - t_oficial).total_seconds() / 60) - TOLERANCIA_MIN)

    # Creamos la nueva fila
    nueva_fila = pd.DataFrame([{
        "DNI": str(dni), "Nombre": nombre, "Fecha": fecha_str,
        "Hora": hora_str, "Tipo": tipo, "Observacion": "", "Tardanza_Min": tardanza
    }])
    
    # Actualizamos la hoja de Google
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    conn.update(data=df_final)
    st.success(f"¡{tipo} registrado en Google Sheets!")

# --- INTERFAZ ---
st.title("🐺 Asistencia Sr. Lobo BPO")
df_empleados = pd.read_csv("empleados.csv")

dni = st.text_input("Ingresa tu DNI:")
if dni:
    persona = df_empleados[df_empleados['DNI'].astype(str) == str(dni)]
    if not persona.empty:
        nombre = persona.iloc[0]['Nombre']
        st.write(f"Bienvenido, **{nombre}**")
        
        c1, c2 = st.columns(2)
        if c1.button("📥 INGRESO"):
            registrar_en_nube(dni, nombre, "INGRESO")
        if c2.button("📤 SALIDA"):
            registrar_en_nube(dni, nombre, "SALIDA")
    else:
        st.error("DNI no registrado.")
