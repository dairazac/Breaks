import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime

# Configuración de la pestaña
st.set_page_config(page_title="Breaks Contact Center", page_icon="☕")

# --- 1. SISTEMA DE LOGIN ---
# Inicializamos el estado de la sesión
if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.nombre = ""
    st.session_state.email = ""

# Si NO está logueado, mostramos la pantalla de login y detenemos la app
if not st.session_state.logueado:
    st.title("🔒 Acceso a Breaks")
    st.write("Por favor, iniciá sesión con tu cuenta de Fu.do")
    
    with st.form("login_form"):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Contraseña / PIN", type="password")
        submit = st.form_submit_button("Ingresar", type="primary")

        if submit:
            try:
                # Verificamos si el email existe en los secrets y la clave coincide
                if email in st.secrets["cuentas"] and st.secrets["cuentas"][email]["password"] == password:
                    st.session_state.logueado = True
                    st.session_state.email = email
                    st.session_state.nombre = st.secrets["cuentas"][email]["nombre"]
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos.")
            except KeyError:
                st.error("Falta configurar la sección [cuentas] en los Secrets.")
    
    st.stop() # Detiene la app acá si no ingresaron

# --- 2. APP PRINCIPAL (Solo se ve si están logueados) ---

# Encabezado con saludo y botón para salir
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.title(f"☕ Hola, {st.session_state.nombre.split()[0]}!")
with col2:
    if st.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.rerun()

st.write("Revisá la tabla y gestioná tu break de 30 min.")

# Conexión con el Sheet
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(worksheet="Hoy", ttl=10)
df_completo["Horario"] = pd.to_datetime(df_completo["Horario"]).dt.strftime('%H:%M')

# --- BOTÓN DE ACTUALIZACIÓN MANUAL ---
if st.button("🔄 Actualizar Tablero"):
    st.cache_data.clear() # Borra cache
    st.rerun() # Recarga la app

# --- VISTA DEL TABLERO ---
st.subheader("📊 Disponibilidad para Hoy")

# Selector de vista
vista = st.radio(
    "Filtrar horarios:",
    ["Disponibles (A partir de ahora)", "Ver todo el día"],
    horizontal=True
)

df_mostrar = df_completo.copy()

# Lógica del filtro de tiempo
if vista == "Disponibles (A partir de ahora)":
    # Obtenemos la hora de Argentina
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_arg)
    
    # Convertimos la hora actual a decimal (ej: 14:30 -> 14.5)
    valor_ahora = ahora.hour + (ahora.minute / 60.0)
    
    # Función para darle valor matemático a los horarios del Excel
    def calcular_valor_horario(hora_str):
        try:
            h, m = map(int, str(hora_str).split(':'))
            return h + (m / 60.0)
        except:
            return 0 # Por si hay un formato raro
            
    # Filtramos la tabla ocultando lo viejo
    df_mostrar["_valor"] = df_mostrar["Horario"].apply(calcular_valor_horario)
    df_mostrar = df_mostrar[df_mostrar["_valor"] >= valor_ahora]
    df_mostrar = df_mostrar.drop(columns=["_valor"])

# Estilo de colores para la tabla
def color_agente(val):
    color = '#28a745' if val == 'Libre' else '#dc3545'
    return f'color: {color}; font-weight: bold'

st.dataframe(
    df_mostrar.style.map(color_agente, subset=['Agente']), 
    use_container_width=True, 
    hide_index=True
)

st.divider()

# --- FORMULARIO DE RESERVA / CANCELACIÓN ---
st.subheader("🙋‍♂️ Reservar break")

# Buscamos si el usuario actual ya tiene alguna fila con su nombre (en la tabla completa)
mi_break_actual = df_completo[df_completo["Agente"] == st.session_state.nombre]

if not mi_break_actual.empty:
    # EL AGENTE YA TIENE UN BREAK AGENDADO
    horario_actual = mi_break_actual.iloc[0]["Horario"]
    st.info(f"✅ Ya tenés un break agendado a las **{horario_actual}**.")
    st.write("¿Te equivocaste o querés cambiar el horario? Primero liberá tu cupo:")
    
    if st.button("🗑️ Eliminar / Liberar mi Break", type="primary"):
        # Pisamos su nombre con "Libre"
        df_completo.loc[df_completo["Horario"] == horario_actual, "Agente"] = "Libre"
        conn.update(worksheet="Hoy", data=df_completo)
        st.cache_data.clear()
        
        st.success("¡Tu break fue eliminado! Ya podés agendar uno nuevo.")
        time.sleep(1.5)
        st.rerun()

else:
    # EL AGENTE NO TIENE BREAK, LE MOSTRAMOS PARA AGENDAR (De la tabla filtrada)
    horarios_libres = df_mostrar[df_mostrar["Agente"] == "Libre"]["Horario"].tolist()

    if not horarios_libres:
        st.warning("¡Todos los horarios están ocupados por hoy!")
    else:
        with st.form("form_reserva"):
            st.write(f"Agendando a nombre de: **{st.session_state.nombre}**")
            horario_elegido = st.selectbox("Elegí el horario", horarios_libres)
            
            btn_reservar = st.form_submit_button("Confirmar Break", type="primary")

            if btn_reservar:
                # Escribimos el nombre del usuario de la sesión directamente
                df_completo.loc[df_completo["Horario"] == horario_elegido, "Agente"] = st.session_state.nombre
                conn.update(worksheet="Hoy", data=df_completo)
                st.cache_data.clear()
                
                st.success(f"¡Listo! Reservaste a las {horario_elegido}")
                st.balloons()
                time.sleep(2)
                st.rerun()
