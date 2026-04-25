import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Configuración de la pestaña
st.set_page_config(page_title="Breaks Contact Center", page_icon="☕")

# 1. Conexión con el Sheet (toma los datos de tu JSON y la URL de los Secrets automáticamente)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Leer la pestaña "Hoy"
# ttl=10 para que refresque cada 10 segundos si alguien entra a mirar
df = conn.read(worksheet="Hoy", ttl=10)

st.title("☕ Gestión de Breaks")
st.write("Seleccioná tu horario.")

# --- VISTA DEL TABLERO ---
st.subheader("📊 Disponibilidad para Hoy")

# Estilo de colores para la tabla
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
st.subheader("🙋‍♂️ Reservar break")

# Filtrar solo horarios que dicen "Libre"
horarios_libres = df[df["Agente"] == "Libre"]["Horario"].tolist()

if not horarios_libres:
    st.warning("¡Todos los horarios están ocupados por hoy!")
else:
    with st.form("form_reserva"):
        nombre_agente = st.text_input("Tu Nombre")
        horario_elegido = st.selectbox("Elegí el horario", horarios_libres)
        
        btn_reservar = st.form_submit_button("Confirmar Break", type="primary")

        if btn_reservar:
            if nombre_agente.strip() == "":
                st.error("Por favor, poné tu nombre.")
            else:
                # 1. Actualizamos el DataFrame temporalmente
                df.loc[df["Horario"] == horario_elegido, "Agente"] = nombre_agente
                
                # 2. Le ordenamos al bot que escriba el cambio en Google Sheets
                conn.update(worksheet="Hoy", data=df)
                
                # 3. PURGAMOS EL CACHÉ: Para que la app "olvide" la tabla vieja
                st.cache_data.clear()
                
                # 4. Mensaje de éxito y globos
                st.success(f"¡Listo {nombre_agente}! Reservaste a las {horario_elegido}")
                st.balloons()
                
                # 5. Esperamos 2 segundos para que se vea el festejo antes de recargar
                time.sleep(2)
                
                # 6. Recargamos la página (ahora traerá la tabla con tu nombre puesto)
                st.rerun()
