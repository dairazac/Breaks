import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime
import extra_streamlit_components as stx

st.set_page_config(page_title="Breaks Contact Center", page_icon="☕", layout="wide")

# ─────────────────────────────────────────────
#  CSS GLOBAL — Dark mode refinado
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* Fuente moderna desde Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #0D1117 !important;
}

/* Reducir padding superior del contenido principal */
[data-testid="stMain"] > div {
    padding-top: 1.2rem !important;
}

/* Alinear columnas al tope — fix del desalineamiento */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: 1.5rem !important;
}

/* ── Encabezado: alineación vertical perfecta ── */
[data-testid="stHorizontalBlock"]:first-of-type {
    align-items: center !important;
    padding-bottom: 0.5rem;
}

/* ── Contenedores con borde ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 14px !important;
    background-color: #161B27 !important;
    padding: 1.2rem 1.4rem !important;
}

/* ── Botones principales ── */
button[kind="primary"],
[data-testid="stFormSubmitButton"] > button,
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #4F7EFF 0%, #3558D4 100%) !important;
    border: none !important;
    border-radius: 9px !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.5rem 1rem !important;
    transition: opacity 0.2s ease, transform 0.1s ease !important;
}
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* ── Botón Cerrar Sesión: outline sutil ── */
[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    color: rgba(255, 255, 255, 0.65) !important;
    font-weight: 400 !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: rgba(255, 255, 255, 0.4) !important;
    color: white !important;
    background: transparent !important;
    opacity: 1 !important;
    transform: none !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
}

/* ── Inputs / Selectbox ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div {
    border-radius: 9px !important;
    border-color: rgba(79, 126, 255, 0.25) !important;
    background-color: #1C2333 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] > div > div:focus {
    border-color: #4F7EFF !important;
    box-shadow: 0 0 0 2px rgba(79, 126, 255, 0.2) !important;
}

/* ── Radio buttons ── */
[data-testid="stRadio"] label {
    font-size: 0.88rem !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background-color: #1C2333 !important;
    border-radius: 10px !important;
    padding: 0.7rem 1rem !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}

/* ── Divisor ── */
hr {
    border-color: rgba(255, 255, 255, 0.07) !important;
    margin: 0.6rem 0 1.2rem 0 !important;
}

/* ── Subheaders ── */
[data-testid="stHeading"] h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    color: #E8EAF0 !important;
    letter-spacing: -0.01em !important;
}

/* ── Alertas / Success / Warning ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}

/* ── Caption ── */
[data-testid="stCaptionContainer"] {
    font-size: 0.78rem !important;
    color: rgba(255,255,255,0.4) !important;
}

/* ── Pantalla de Login: centrar contenido ── */
.login-wrapper {
    max-width: 420px;
    margin: 3rem auto 0 auto;
    padding: 2rem;
    background: #161B27;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.07);
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  GESTIÓN DE COOKIES
# ─────────────────────────────────────────────
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.nombre = ""
    st.session_state.email = ""

if not st.session_state.logueado:
    saved_email = cookie_manager.get('fudo_user_email')
    if saved_email and saved_email in st.secrets["cuentas"]:
        st.session_state.logueado = True
        st.session_state.email = saved_email
        st.session_state.nombre = st.secrets["cuentas"][saved_email]["nombre"]


# ─────────────────────────────────────────────
#  PANTALLA DE LOGIN
# ─────────────────────────────────────────────
if not st.session_state.logueado:

    # Centrar el login con columnas
    _, col_centro, _ = st.columns([1, 1.2, 1])

    with col_centro:
        st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
        st.image("logo.png", width=160)
        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

        st.markdown("""
            <h2 style='margin:0 0 0.3rem 0; font-size:1.5rem; font-weight:700; color:#E8EAF0;'>
                Acceso a Breaks ☕
            </h2>
            <p style='color:rgba(255,255,255,0.45); font-size:0.88rem; margin-bottom:1.5rem;'>
                Tu sesión se mantendrá activa por 60 días.
            </p>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email corporativo", placeholder="nombre@empresa.com").strip().lower()
            password = st.text_input("Contraseña / PIN", type="password", placeholder="••••••")
            submit = st.form_submit_button("Ingresar →", use_container_width=True)

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


# ─────────────────────────────────────────────
#  APP PRINCIPAL — Leer datos
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(worksheet="Hoy", ttl=10)
df_completo["Horario"] = pd.to_datetime(df_completo["Horario"]).dt.strftime('%H:%M')


# ─────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────
col_logo, col_saludo, col_salir = st.columns([0.15, 0.65, 0.20], vertical_alignment="center")

with col_logo:
    st.image("logo.png", width=150)

with col_saludo:
    nombre_corto = st.session_state.nombre.split()[0]
    st.markdown(
        f"""
        <h2 style='margin:0; font-weight:700; font-size:1.4rem; color:#E8EAF0; 
                   letter-spacing:-0.02em; line-height:1;'>
            ☕ &nbsp;Hola, {nombre_corto}!
        </h2>
        <p style='margin:0.15rem 0 0 0; color:rgba(255,255,255,0.35); 
                  font-size:0.78rem; letter-spacing:0.01em;'>
            Contact Center · Breaks
        </p>
        """,
        unsafe_allow_html=True
    )

with col_salir:
    if st.button("Cerrar Sesión", use_container_width=True, type="secondary"):
        cookie_manager.delete('fudo_user_email')
        st.session_state.logueado = False
        st.rerun()

st.divider()


# ─────────────────────────────────────────────
#  COLUMNAS PRINCIPALES
# ─────────────────────────────────────────────
col_izq, col_der = st.columns([0.58, 0.42], gap="large")


# ══════════════════════════════════════════════
#  COLUMNA IZQUIERDA — Tablero de disponibilidad
# ══════════════════════════════════════════════
with col_izq:
    with st.container(border=True):
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
                except:
                    return 0

            df_mostrar["_valor"] = df_mostrar["Horario"].apply(calcular_valor_horario)
            df_mostrar = df_mostrar[df_mostrar["_valor"] >= valor_ahora]
            df_mostrar = df_mostrar.drop(columns=["_valor"])

        tiempos = pd.to_datetime(df_mostrar["Horario"], format='%H:%M')
        tiempos_fin = (tiempos + pd.Timedelta(minutes=15)).dt.strftime('%H:%M')
        df_mostrar["Bloque"] = df_mostrar["Horario"] + " → " + tiempos_fin

        # Métricas rápidas
        total = len(df_mostrar)
        libres = len(df_mostrar[df_mostrar["Agente"] == "Libre"])
        ocupados = total - libres

        m1, m2, m3 = st.columns(3)
        m1.metric("Total bloques", total)
        m2.metric("🟢 Libres", libres)
        m3.metric("🔴 Ocupados", ocupados)

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

        # Colores del dataframe — elegantes, no chillones
        def color_fila(row):
            if row['Agente'] == 'Libre':
                return [
                    'background-color: rgba(34, 197, 94, 0.07); '
                    'color: #4ADE80; '
                    'font-weight: 500'
                ] * len(row)
            else:
                return [
                    'background-color: rgba(239, 68, 68, 0.07); '
                    'color: #F87171; '
                    'font-weight: 500'
                ] * len(row)

        st.dataframe(
            df_mostrar[["Bloque", "Agente"]].style.apply(color_fila, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.caption("↻ Se actualiza automáticamente cada 10 segundos")


# ══════════════════════════════════════════════
#  COLUMNA DERECHA — Panel de acción
# ══════════════════════════════════════════════
with col_der:
    with st.container(border=True):
        st.subheader("🙋‍♂️ Mi Break")

        mi_break_actual = df_completo[df_completo["Agente"] == st.session_state.nombre]

        if not mi_break_actual.empty:
            horario_actual = mi_break_actual.iloc[0]["Horario"]

            # Card de estado del break
            st.markdown(f"""
                <div style='
                    background: rgba(79, 126, 255, 0.1);
                    border: 1px solid rgba(79, 126, 255, 0.25);
                    border-radius: 10px;
                    padding: 1rem 1.2rem;
                    margin-bottom: 1rem;
                '>
                    <div style='font-size:0.75rem; color:rgba(255,255,255,0.45); 
                                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.3rem;'>
                        Break agendado
                    </div>
                    <div style='font-size:1.6rem; font-weight:700; color:#E8EAF0; line-height:1;'>
                        {horario_actual}
                    </div>
                    <div style='font-size:0.82rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;'>
                        Duración: 30 minutos
                    </div>
                </div>
            """, unsafe_allow_html=True)

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
                if df_mostrar.iloc[i]["Agente"] == "Libre" and df_mostrar.iloc[i + 1]["Agente"] == "Libre":
                    horarios_libres.append(df_mostrar.iloc[i]["Horario"])

            if not horarios_libres:
                st.warning("¡No hay bloques de 30 min libres disponibles!")

            else:
                # Info del agente
                st.markdown(f"""
                    <div style='
                        background: rgba(255,255,255,0.04);
                        border-radius: 8px;
                        padding: 0.6rem 0.9rem;
                        margin-bottom: 0.8rem;
                        font-size: 0.85rem;
                        color: rgba(255,255,255,0.55);
                    '>
                        Agendando para: &nbsp;
                        <span style='color:#E8EAF0; font-weight:600;'>
                            {st.session_state.nombre}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                with st.form("form_reserva"):
                    horario_elegido = st.selectbox("⏰ Horario de inicio", horarios_libres)
                    st.caption("🔒 Se bloquearán 2 turnos de 15 min consecutivos.")
                    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                    btn_reservar = st.form_submit_button("☕ Confirmar Break", use_container_width=True)

                    if btn_reservar:
                        idx_inicio = df_completo[df_completo["Horario"] == horario_elegido].index[0]
                        df_completo.loc[idx_inicio, "Agente"] = st.session_state.nombre
                        if (idx_inicio + 1) in df_completo.index:
                            df_completo.loc[idx_inicio + 1, "Agente"] = st.session_state.nombre

                        conn.update(worksheet="Hoy", data=df_completo)

                        try:
                            url_slack = st.secrets["slack_webhook"]
                            mensaje = {"text": f"☕ *{st.session_state.nombre}* agendó su break a las *{horario_elegido}* hs."}
                            response = requests.post(url_slack, json=mensaje)
                            st.write(f"Slack status: {response.status_code} — {response.text}")
                        except Exception as e:
                            st.error(f"Error Slack: {e}")

                        st.cache_data.clear()
                        st.success(f"¡Listo! Reservaste a las {horario_elegido} 🎉")
                        st.balloons()
                        time.sleep(15)
                        st.rerun()
