import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Tablero de Breaks", layout="centered")

# 1. Función para generar los bloques de 9:00 AM a 1:00 AM (32 bloques de 30 min)
def generar_slots():
    slots = []
    # Usamos una fecha base cualquiera solo para la matemática de las horas
    hora_actual = datetime(2000, 1, 1, 9, 0) 
    hora_fin = datetime(2000, 1, 2, 1, 0) # 1 AM del día siguiente
    
    while hora_actual < hora_fin:
        hora_str = hora_actual.strftime("%H:%M")
        slots.append(hora_str)
        hora_actual += timedelta(minutes=30)
    return slots

# 2. Inicializar el estado de la app (Nuestra base de datos temporal)
if 'agenda' not in st.session_state:
    st.session_state.agenda = {slot: "Libre" for slot in generar_slots()}

st.title("☕ Tablero de Breaks (30 min)")
st.write("Horario de atención: 09:00 a 01:00")

# --- SECCIÓN VISUAL: LA GRILLA ---
st.subheader("👀 Estado Actual del Día")

# Convertimos el diccionario a un DataFrame para que se vea lindo en pantalla
df_agenda = pd.DataFrame(list(st.session_state.agenda.items()), columns=["Horario", "Agente"])
# Aplicamos un poco de color: verde si está libre, rojo/gris si está ocupado
def color_libre(val):
    color = '#28a745' if val == 'Libre' else '#dc3545'
    return f'color: {color}; font-weight: bold'

st.dataframe(df_agenda.style.map(color_libre, subset=['Agente']), use_container_width=True, hide_index=True)

st.divider()

# --- SECCIÓN DE RESERVA ---
st.subheader("🔒 Bloquear tu Horario")

# Filtramos solo los horarios que siguen "Libres"
horarios_libres = [slot for slot, estado in st.session_state.agenda.items() if estado == "Libre"]

col1, col2 = st.columns(2)
with col1:
    agente_nombre = st.text_input("Tu Nombre (Ej: Alexis, Enzo)")
with col2:
    horario_elegido = st.selectbox("Selecciona un horario disponible", horarios_libres)

if st.button("Reservar Break", type="primary"):
    if agente_nombre.strip() == "":
        st.error("Por favor, ingresa tu nombre.")
    else:
        st.session_state.agenda[horario_elegido] = agente_nombre
        st.success(f"¡Joya! {agente_nombre} se agendó a las {horario_elegido}.")
        st.rerun() # Actualiza la pantalla al instante

st.divider()

# --- SECCIÓN ADMIN: RESUMEN PARA TI ---
with st.expander("👑 Zona Admin: Resumen del Día"):
    st.write("Aquí puedes copiar el resumen de los que ya agendaron hoy:")
    resumen = {h: a for h, a in st.session_state.agenda.items() if a != "Libre"}
    
    if resumen:
        for h, a in resumen.items():
            st.write(f"- **{h}**: {a}")
    else:
        st.write("Nadie ha agendado todavía.")
        
    # En el futuro, aquí podríamos poner un botón "Enviar resumen a Slack"
