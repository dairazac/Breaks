import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime
import extra_streamlit_components as stx

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
    if saved_email and saved_email in st.secrets["cuentas"]:
        st.session_state.logueado = True
        st.session_state.email = saved_email
        st.session_state.nombre = st.secrets["cuentas"][saved_email]["nombre"]

# --- 1. PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.image("logo.png", width=150)
    st.title("🔒 Acceso a Breaks")
    st.write("Iniciá sesión. Se mantendrá abierta en este navegador.")
    
    with st.form("login_form"):
        email = st.text_input("Email corporativo").strip().lower()
        password = st.text_input("Contraseña / PIN", type="password")
        
        # Botón minimalista (sin type="primary")
        submit = st.form_submit_button("Ingresar")

        if submit:
            try:
                if email in st.secrets["cuentas"] and st.secrets["cuentas"][email]["password"] == password:
                    st.session_state.logueado = True
                    st.session_state.email = email
                    st.session_state.nombre = st.secrets["cuentas"][email]["nombre"]
                    
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

# --- ENCABEZADO SUPERIOR ALINEADO ---
col_logo, col_saludo, col_salir = st.columns([0.15, 0.7, 0.15], vertical_alignment="center")

with col_logo:
    st.image("logo.png", width=120)

with col_saludo:
    st.header(f" Hola, {st.session_state.nombre.split()[0]}!")

with col_salir:
    if st.button("Cerrar Sesión", use_container_width=True):
        cookie_manager.delete('fudo_user_email')
        st.session_state.logueado = False
        st.rerun()

st.divider()

# --- DIVISIÓN EN DOS COLUMNAS PRINCIPALES ---
col_izq, col_der = st.columns([0.6, 0.4], gap="large")

with col_izq:
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

    tiempos = pd.to_datetime(df_mostrar["Horario"], format='%H:%M')
    tiempos_fin = (tiempos + pd.Timedelta(minutes=15)).dt.strftime('%H:%M')
    df_mostrar["Bloque"] = df_mostrar["Horario"] + " - " + tiempos_fin

    def color_fila(row):
        if row['Agente'] == 'Libre':
            # Fondo verde traslúcido, texto verde neón (da mucha vida)
            return ['background-color: rgba(40, 167, 69, 0.2); color: #00FF88; font-weight: bold'] * len(row)
        else:
            # Fondo rojo traslúcido, texto rojo vibrante
            return ['background-color: rgba(220, 53, 69, 0.2); color: #FF4D4D; font-weight: bold'] * len(row)
            
    st.dataframe(
        df_mostrar[["Bloque", "Agente"]].style.apply(color_fila, axis=1), 
        use_container_width=True, 
        hide_index=True
    )

with col_der:
    
    # --- FORMULARIO DE RESERVA / CANCELACIÓN ---
    st.subheader("☕ Mi Break")

    mi_break_actual = df_completo[df_completo["Agente"] == st.session_state.nombre]

    if not mi_break_actual.empty:
        horario_actual = mi_break_actual.iloc[0]["Horario"]
        st.success(f"✅ Ya tenés un break agendado desde las **{horario_actual}** (30 min).")
        
        if st.button("🗑️ Eliminar / Liberar mi Break", use_container_width=True):
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
            st.warning("¡No hay bloques de 30 min libres!")
        else:
            with st.form("form_reserva"):
                st.write(f"Agendando para: **{st.session_state.nombre}**")
                horario_elegido = st.selectbox("Elegí el horario de inicio", horarios_libres)
                
                st.caption("🔒 Se bloquearán 2 turnos de 15 min consecutivos.")
                
                btn_reservar = st.form_submit_button("Confirmar Break", use_container_width=True)

                if btn_reservar:
                    idx_inicio = df_completo[df_completo["Horario"] == horario_elegido].index[0]
                    df_completo.loc[idx_inicio, "Agente"] = st.session_state.nombre
                    if (idx_inicio + 1) in df_completo.index:
                        df_completo.loc[idx_inicio + 1, "Agente"] = st.session_state.nombre
                    
                    conn.update(worksheet="Hoy", data=df_completo)

                    try:
                        url_slack = st.secrets["slack_webhook"]
                        mensaje = {"text": f"☕ *{st.session_state.nombre}* agendó su break a las *{horario_elegido}* hs."}
                        requests.post(url_slack, json=mensaje)
                    except Exception as e: 
                        st.warning("⚠️ El break se guardó, pero falló la notificación a Slack.")
                    
                    st.cache_data.clear()
                    st.success(f"¡Listo! Reservaste a las {horario_elegido}")
                    st.balloons()
                    time.sleep(5)
                    st.rerun()
