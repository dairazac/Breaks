import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Breaks Contact Center", page_icon="☕")

# 1. Conexión con el Sheet
# Importante: En los Secrets de Streamlit debes configurar la URL
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Leer la pestaña "Hoy"
# ttl=10 para que refresque cada 10 segundos si alguien cambia algo
df = conn.read(worksheet="Hoy", ttl=10)

st.title("☕ Gestión de Breaks")
st.write("Seleccioná tu horario. Recordá que el break es de 30 min.")

# --- VISTA DEL TABLERO ---
st.subheader("📊 Disponibilidad para Hoy")

# Estilo para la tabla
def color_agente(val):
    color = '#28a745' if val == 'Libre' else '#dc3545'
    return f'color: {color}; font-weight: bold'

st.dataframe(
    df.style.map(color_agente, subset=['Agente']), 
    use_container_width=True, 
    hide_index=True
)

st.divider()

# --- FORMULARIO DE RESERVA ---
st.subheader("🙋‍♂️ Reservar mi lugar")

# Filtrar solo horarios que están "Libre"
horarios_libres = df[df["Agente"] == "Libre"]["Horario"].tolist()

if not horarios_disponibles:
    st.warning("¡Todos los horarios están ocupados!")
else:
    with st.form("form_reserva"):
        # Podés cambiar esto por un selectbox con nombres fijos si preferís
        nombre_agente = st.text_input("Tu Nombre")
        horario_elegido = st.selectbox("Elegí el horario", horarios_libres)
        
        btn_reservar = st.form_submit_button("Confirmar Break", type="primary")

        if btn_reservar:
            if nombre_agente.strip() == "":
                st.error("Por favor, poné tu nombre.")
            else:
                # Actualizar localmente
                df.loc[df["Horario"] == horario_elegido, "Agente"] = nombre_agente
                
                # Subir el cambio a la pestaña "Hoy" de Google Sheets
                conn.update(worksheet="Hoy", data=df)
                
                st.success(f"¡Listo {nombre_agente}! Reservaste a las {horario_elegido}")
                st.balloons()
                st.rerun()
