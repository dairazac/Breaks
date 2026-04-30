import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime
import extra_streamlit_components as stx # <-- Nueva librería para cookies

# Configuración de la pestaña (¡Agregamos layout="wide"!)
st.set_page_config(page_title="Breaks Contact Center", page_icon="☕", layout="wide")

# --- 🍪 GESTIÓN DE COOKIES ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# Inicializamos el estado de la sesión si no existe
if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.nombre = ""
    st.session_state.email = ""

# 1. Intentamos recuperar sesión desde la Cookie si no está logueado en session_state
if not st.session_state.logueado:
    saved_email = cookie_manager.get('fudo_user_email')
    if saved_email:
        # Si existe la cookie, verificamos que el mail siga siendo válido en Secrets
        if saved_email in st.secrets["cuentas"]:
            st.session_state.logueado = True
            st.session_state.email = saved_email
            st.session_state.nombre = st.secrets["cuentas"][saved_email]["nombre"]

# --- 1. PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    # st.image("logo.png", width=150) # Descomentá esta línea y subí un logo.png a tu GitHub
    st.title("🔒 Acceso a Breaks")
    st.write("Iniciá sesión. Se mantendrá abierta en este navegador.")
    
    with st.form("login_form"):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Contraseña / PIN", type="password")
        submit = st.form_submit_button("Ingresar", type="primary")

        if submit:
            try:
                if email in st.secrets["cuentas"] and st.secrets["cuentas"][email]["password"] == password:
                    # Guardamos en Session State
                    st.session_state.logueado = True
                    st.session_state.email = email
                    st.session_state.nombre = st.secrets["cuentas"][email]["nombre"]
                    
                    # 🍪 GUARDAMOS LA COOKIE (Conservé tus 60 días)
                    cookie_manager.set('fudo_user_email', email, expires_at=datetime.now() + pd.Timedelta(days=60))
                    
                    st.success("¡Sesión iniciada!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos.")
            except KeyError:
                st.error("Falta configurar la sección [cuentas] en los Secrets.")
    
    st.stop()

# --- 2. APP PRINCIPAL ---

# Conexión con el Sheet
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(worksheet="Hoy", ttl=10)
df_completo["Horario"] = pd.to_datetime(df_completo["Horario"]).dt.strftime('%H:%M')

# --- ENCABEZADO SUPERIOR CON ESPACIO PARA LOGO ---
col_logo, col_saludo, col_salir = st.columns([0.15, 0.7, 0.15])
with col_logo:
    pass # ACÁ VA EL LOGO: st.image("logo.png", width=120)
with col_saludo:
    st.title(f"☕ Hola, {st.session_state.nombre.split()[0]}!")
with col_salir:
    st.write("") # Espaciador para bajar un poquito el botón
    if st.button("Cerrar Sesión"):
        # Al cerrar sesión, borramos la cookie para que pida clave de nuevo
        cookie_manager.delete('fudo_user_email')
        st.session_state.logueado = False
        st.rerun()

st.divider()

# --- DIVISIÓN EN DOS COLUMNAS PRINCIPALES ---
col_izq, col_der = st.columns([0.6, 0.4], gap="large")

with col_izq:
    # --- VISTA DEL TABLERO ---
    st.subheader("📊 Disponibilidad para Hoy")

    vista = st.radio(
        "Filtrar horarios:",
        ["Disponibles (A partir de ahora)", "Ver todo el día"],
        horizontal=True
    )

    df_mostrar = df_completo.copy()

    if vista == "Disponibles (A partir de ahora)":
        tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
        ahora = datetime.now(tz_arg)
        valor_ahora = ahora.hour + (ahora.minute / 60.0)
        
        def calcular_valor_horario(hora_str):
            try:
                h, m = map(int, str(hora_str).split(':'))
                return h + (m / 60.0)
            except: return 0 
                
        df_mostrar["_valor"] = df_mostrar["Horario"].apply(calcular_valor_horario)
        df_mostrar = df_mostrar[df_mostrar["_valor"] >= valor_ahora]
        df_mostrar = df_mostrar.drop(columns=["_valor"])

    # Magia visual de rangos
    tiempos = pd.to_datetime(df_mostrar["Horario"], format='%H:%M')
    tiempos_fin = (tiempos + pd.Timedelta(minutes=15)).dt.strftime('%H:%M')
    df_mostrar["Bloque"] = df_mostrar["Horario"] + " - " + tiempos_fin

    # Nuevo estilo de colores: Pinta toda la fila (Fondo + Texto)
    def color_fila(row):
        if row['Agente'] == 'Libre':
            # Verde oscuro para fondo, verde claro para texto
            return ['background-color: #0d2b1b; color: #a3e635; font-weight: bold'] * len(row)
        else:
            # Rojo oscuro para fondo, rojo claro para texto
            return ['background-color: #3b0918; color: #f87171; font-weight: bold'] * len(row)

    st.dataframe(
        df_mostrar[["Bloque", "Agente"]].style.apply(color_fila, axis=1), 
        use_container_width=True, 
        hide_index=True
    )

with col_der:
    st.subheader("⚙️ Panel de Control")
    
    # --- BOTÓN DE ACTUALIZACIÓN MANUAL ---
    if st.button("🔄 Actualizar Tabla manualmente", use_container_width=True):
        st.cache_data.clear() 
        st.rerun() 
        
    st.write("") # Espaciador
    
    # --- FORMULARIO DE RESERVA / CANCELACIÓN ---
    st.subheader("🙋‍♂️ Mi Break")

    mi_break_actual = df_completo[df_completo["Agente"] == st.session_state.nombre]

    if not mi_break_actual.empty:
        horario_actual = mi_break_actual.iloc[0]["Horario"]
        st.success(f"✅ Ya tenés un break agendado desde las **{horario_actual}** (30 min).")
        
        if st.button("🗑️ Eliminar / Liberar mi Break", type="primary", use_container_width=True):
            df_completo.loc[df_completo["Agente"] == st.session_state.nombre, "Agente"] = "Libre"
            conn.update(worksheet="Hoy", data=df_completo)
            st.cache_data.clear()
            st.success("¡Tu break fue eliminado!")
            time.sleep(1.5)
            st.rerun()

    else:
        horarios_libres = []
        for i in range(len(df_mostrar) - 1):
            if df_mostrar.iloc[i]["Agente"] == "Libre" and df_mostrar.iloc[i+1]["Agente"] == "Libre":
                horarios_libres.append(df_mostrar.iloc[i]["Horario"])

        if not horarios_libres:
            st
