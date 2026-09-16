import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime
import extra_streamlit_components as stx
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Breaks Contact Center", page_icon="☕", layout="wide")
st_autorefresh(interval=15000, key="autorefresh")

# ─────────────────────────────────────────────
#  GESTIÓN DE COOKIES
# ─────────────────────────────────────────────
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# ─────────────────────────────────────────────
#  TEMA (oscuro / claro) — cada agente elige el suyo desde
#  la app y se guarda 60 días en su navegador, igual que el login.
# ─────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#0D1117",
        "card_bg": "#161B27",
        "card_border": "rgba(255,255,255,0.07)",
        "input_bg": "#1C2333",
        "input_border": "rgba(79,126,255,0.25)",
        "input_border_focus": "#4F7EFF",
        "text": "#E8EAF0",
        "heading": "#E8EAF0",
        "muted": "rgba(255,255,255,0.45)",
        "muted_soft": "rgba(255,255,255,0.35)",
        "banner_bg": "rgba(255,255,255,0.04)",
        "divider": "rgba(255,255,255,0.07)",
        "accent": "#4F7EFF",
        "accent_grad": "linear-gradient(135deg, #4F7EFF 0%, #3558D4 100%)",
        "accent_soft_bg": "rgba(79,126,255,0.10)",
        "accent_soft_border": "rgba(79,126,255,0.25)",
        "row_free_bg": "rgba(34,197,94,0.07)",
        "row_free_text": "#4ADE80",
        "row_busy_bg": "rgba(239,68,68,0.07)",
        "row_busy_text": "#F87171",
        "secondary_border": "rgba(255,255,255,0.18)",
        "secondary_text": "rgba(255,255,255,0.65)",
        "secondary_hover_border": "rgba(255,255,255,0.4)",
        "metric_bg": "#1C2333",
    },
    "light": {
        "bg": "#F3E9DC",
        "card_bg": "#FFFFFF",
        "card_border": "rgba(120,80,40,0.14)",
        "input_bg": "#FBF6EF",
        "input_border": "rgba(216,130,60,0.35)",
        "input_border_focus": "#D9822B",
        "text": "#3B2E24",
        "heading": "#2B2017",
        "muted": "rgba(59,46,36,0.60)",
        "muted_soft": "rgba(59,46,36,0.50)",
        "banner_bg": "rgba(120,80,40,0.07)",
        "divider": "rgba(120,80,40,0.16)",
        "accent": "#D9822B",
        "accent_grad": "linear-gradient(135deg, #E8934A 0%, #D9682B 100%)",
        "accent_soft_bg": "rgba(217,130,43,0.12)",
        "accent_soft_border": "rgba(217,130,43,0.30)",
        "row_free_bg": "rgba(30,122,52,0.12)",
        "row_free_text": "#1E7A34",
        "row_busy_bg": "rgba(178,61,36,0.12)",
        "row_busy_text": "#B23D24",
        "secondary_border": "rgba(120,80,40,0.28)",
        "secondary_text": "rgba(59,46,36,0.70)",
        "secondary_hover_border": "rgba(120,80,40,0.55)",
        "metric_bg": "#FBF6EF",
    },
}

_tema_guardado = cookie_manager.get('fudo_theme')
if _tema_guardado not in ("dark", "light"):
    _tema_guardado = "dark"
if "tema" not in st.session_state:
    st.session_state.tema = _tema_guardado

th = THEMES[st.session_state.tema]

def _cambiar_tema(nuevo):
    if nuevo != st.session_state.tema:
        st.session_state.tema = nuevo
        cookie_manager.set('fudo_theme', nuevo, expires_at=datetime.now() + pd.Timedelta(days=60))
        st.rerun()

def selector_tema(key):
    opciones = ["dark", "light"]
    etiquetas = {"dark": "🌙 Oscuro", "light": "☀️ Claro"}
    elegido = st.radio(
        "Tema", opciones, index=opciones.index(st.session_state.tema),
        format_func=lambda o: etiquetas[o], horizontal=True,
        label_visibility="collapsed", key=key
    )
    _cambiar_tema(elegido)


# ─────────────────────────────────────────────
#  CSS GLOBAL — se arma según el tema elegido (oscuro/claro)
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
/* Fuente moderna desde Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
    font-family: 'DM Sans', sans-serif !important;
    background-color: {th['bg']} !important;
    color: {th['text']} !important;
}}

/* Etiquetas de los campos (inputs, selects, radios) y texto general:
   sin esto, en modo claro quedarían con el color de texto claro del
   tema base de Streamlit y se leerían mal sobre fondo blanco. */
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p,
label {{
    color: {th['text']} !important;
}}

/* Reducir padding superior del contenido principal */
[data-testid="stMain"] > div {{
    padding-top: 1.2rem !important;
}}

/* Alinear columnas al tope — fix del desalineamiento */
[data-testid="stHorizontalBlock"] {{
    align-items: flex-start !important;
    gap: 1.5rem !important;
}}

/* ── Encabezado: alineación vertical perfecta ── */
[data-testid="stHorizontalBlock"]:first-of-type {{
    align-items: center !important;
    padding-bottom: 0.5rem;
}}

/* ── Contenedores con borde ── */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid {th['card_border']} !important;
    border-radius: 16px !important;
    background-color: {th['card_bg']} !important;
    padding: 1.3rem 1.5rem !important;
}}

/* ── Panel "Mi Break": acento a la izquierda para resaltar
     que es la acción personal del agente, no solo información ── */
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] {{
    border-left: 3px solid {th['accent']} !important;
}}

/* ── Botones principales ── */
button[kind="primary"],
[data-testid="stFormSubmitButton"] > button,
[data-testid="stButton"] > button {{
    background: {th['accent_grad']} !important;
    border: none !important;
    border-radius: 9px !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.5rem 1rem !important;
    transition: opacity 0.2s ease, transform 0.1s ease !important;
}}
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stButton"] > button:hover {{
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}}

/* ── Botón Cerrar Sesión: outline sutil ── */
[data-testid="stButton"] > button[kind="secondary"] {{
    background: transparent !important;
    border: 1px solid {th['secondary_border']} !important;
    color: {th['secondary_text']} !important;
    font-weight: 400 !important;
}}
[data-testid="stButton"] > button[kind="secondary"]:hover {{
    border-color: {th['secondary_hover_border']} !important;
    color: {th['text']} !important;
    background: transparent !important;
    opacity: 1 !important;
    transform: none !important;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid {th['card_border']} !important;
}}

/* ── Inputs / Selectbox ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div {{
    border-radius: 9px !important;
    border-color: {th['input_border']} !important;
    background-color: {th['input_bg']} !important;
    color: {th['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] > div > div:focus {{
    border-color: {th['input_border_focus']} !important;
    box-shadow: 0 0 0 2px {th['accent_soft_bg']} !important;
}}
/* Lista desplegable del selectbox (se renderiza aparte, es lo más
   frágil de ajustar por tema porque no depende de nuestro CSS de card) */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {{
    background-color: {th['card_bg']} !important;
}}
[data-baseweb="menu"] li,
[data-baseweb="menu"] li * {{
    color: {th['text']} !important;
}}

/* ── Radio / filtros como selector tipo "segmented control" ── */
[data-testid="stRadio"] > div {{
    gap: 0.4rem !important;
}}
[data-testid="stRadio"] label {{
    font-size: 0.85rem !important;
    font-family: 'DM Sans', sans-serif !important;
    background: {th['banner_bg']} !important;
    border: 1px solid {th['card_border']} !important;
    border-radius: 8px !important;
    padding: 0.35rem 0.75rem !important;
    margin: 0 !important;
}}

/* ── Métricas ── */
[data-testid="stMetric"] {{
    background-color: {th['metric_bg']} !important;
    border-radius: 10px !important;
    padding: 0.7rem 1rem !important;
    border: 1px solid {th['card_border']} !important;
}}
[data-testid="stMetricValue"] {{
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
    color: {th['heading']} !important;
}}

/* ── Divisor ── */
hr {{
    border-color: {th['divider']} !important;
    margin: 0.6rem 0 1.2rem 0 !important;
}}

/* ── Subheaders ── */
[data-testid="stHeading"] h3 {{
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    color: {th['heading']} !important;
    letter-spacing: -0.01em !important;
}}

/* ── Alertas / Success / Warning ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}}

/* ── Caption ── */
[data-testid="stCaptionContainer"] {{
    font-size: 0.78rem !important;
    color: {th['muted_soft']} !important;
}}

/* ── Pantalla de Login: centrar contenido ── */
.login-wrapper {{
    max-width: 420px;
    margin: 3rem auto 0 auto;
    padding: 2rem;
    background: {th['card_bg']};
    border-radius: 16px;
    border: 1px solid {th['card_border']};
}}
</style>
""", unsafe_allow_html=True)

if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.ignorar_cookie = False # Creamos nuestra variable escudo

if not st.session_state.logueado:
    # Si acabamos de cerrar sesión, ignoramos la cookie por este turno
    if st.session_state.get("ignorar_cookie", False):
        st.session_state.ignorar_cookie = False # Apagamos el escudo
    else:
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

        col_logo_login, col_tema_login = st.columns([0.62, 0.38])
        with col_logo_login:
            st.image("logo.png", width=160)
        with col_tema_login:
            selector_tema("tema_login")

        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

        st.markdown(f"""
            <h2 style='margin:0 0 0.3rem 0; font-size:1.5rem; font-weight:700; color:{th["heading"]};'>
                Acceso a Breaks ☕
            </h2>
            <p style='color:{th["muted"]}; font-size:0.88rem; margin-bottom:1.5rem;'>
                Tu sesión se mantendrá activa por 60 días.
            </p>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email corporativo", placeholder="Correo electrónico").strip().lower()
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
#  CURVA DE DEMANDA (opcional) — sugiere los mejores horarios
#  Lee la hoja "Demanda" (Horario | Nivel: Bajo/Medio/Alto).
#  Si la hoja no existe o falla la lectura, la app sigue
#  funcionando normal, solo sin las sugerencias.
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def cargar_mapa_demanda():
    try:
        df_dem = conn.read(worksheet="Demanda", ttl=300)
        df_dem["Horario"] = pd.to_datetime(df_dem["Horario"]).dt.strftime('%H:%M')
        return dict(zip(df_dem["Horario"], df_dem["Nivel"]))
    except Exception:
        return {}

mapa_demanda = cargar_mapa_demanda()
ORDEN_NIVEL = {"Bajo": 0, "Medio": 1, "Alto": 2}

def nivel_de(horario):
    return mapa_demanda.get(horario, "Medio")


# ─────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────
col_logo, col_saludo, col_tema, col_salir = st.columns([0.14, 0.51, 0.15, 0.20], vertical_alignment="center")

with col_logo:
    st.image("logo.png", width=150)

with col_saludo:
    nombre_corto = st.session_state.nombre.split()[0]
    st.markdown(
        f"""
        <h2 style='margin:0; font-weight:700; font-size:1.4rem; color:{th["heading"]};
                   letter-spacing:-0.02em; line-height:1;'>
            ☕ &nbsp;Hola, {nombre_corto}!
        </h2>
        <p style='margin:0.15rem 0 0 0; color:{th["muted_soft"]};
                  font-size:0.78rem; letter-spacing:0.01em;'>
            Contact Center · Breaks
        </p>
        """,
        unsafe_allow_html=True
    )

with col_tema:
    selector_tema("tema_dashboard")

with col_salir:
    if st.button("Cerrar Sesión", use_container_width=True, type="secondary"):
        cookie_manager.delete('fudo_user_email')
        st.session_state.logueado = False
        st.session_state.ignorar_cookie = True # Prendemos el escudo antes de reiniciar
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

        # Sugerencia según curva de demanda (solo para bloques libres)
        def _etiqueta_sugerencia(row):
            if row["Agente"] != "Libre" or not mapa_demanda:
                return ""
            nivel = nivel_de(row["Horario"])
            if nivel == "Bajo":
                return "🟢 Recomendado"
            elif nivel == "Alto":
                return "🔴 Alta demanda"
            return ""

        df_mostrar["Sugerencia"] = df_mostrar.apply(_etiqueta_sugerencia, axis=1)

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
                    f'background-color: {th["row_free_bg"]}; '
                    f'color: {th["row_free_text"]}; '
                    'font-weight: 500'
                ] * len(row)
            else:
                return [
                    f'background-color: {th["row_busy_bg"]}; '
                    f'color: {th["row_busy_text"]}; '
                    'font-weight: 500'
                ] * len(row)

        columnas_tabla = ["Bloque", "Agente", "Sugerencia"] if mapa_demanda else ["Bloque", "Agente"]
        st.dataframe(
            df_mostrar[columnas_tabla].style.apply(color_fila, axis=1),
            use_container_width=True,
            hide_index=True
        )

        if mapa_demanda:
            st.caption("↻ Se actualiza automáticamente cada 10 segundos · 🟢 Recomendado = baja demanda esperada · 🔴 Alta demanda = mejor evitarlo si se puede")
        else:
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
                    background: {th["accent_soft_bg"]};
                    border: 1px solid {th["accent_soft_border"]};
                    border-radius: 10px;
                    padding: 1rem 1.2rem;
                    margin-bottom: 1rem;
                '>
                    <div style='font-size:0.75rem; color:{th["muted"]};
                                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.3rem;'>
                        Break agendado
                    </div>
                    <div style='font-size:1.6rem; font-weight:700; color:{th["heading"]}; line-height:1;'>
                        {horario_actual}
                    </div>
                    <div style='font-size:0.82rem; color:{th["muted_soft"]}; margin-top:0.3rem;'>
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

            # Ordenamos mostrando primero los bloques de menor demanda (sugeridos),
            # sin restringir: el agente puede elegir cualquier horario libre.
            if mapa_demanda:
                horarios_libres.sort(key=lambda h: ORDEN_NIVEL.get(nivel_de(h), 1))

            def _etiqueta_opcion(h):
                if not mapa_demanda:
                    return h
                nivel = nivel_de(h)
                if nivel == "Bajo":
                    return f"🟢 {h} · Recomendado"
                elif nivel == "Alto":
                    return f"🔴 {h} · Alta demanda"
                return h

            if not horarios_libres:
                st.warning("¡No hay bloques de 30 min libres disponibles!")

            else:
                # Info del agente
                st.markdown(f"""
                    <div style='
                        background: {th["banner_bg"]};
                        border-radius: 8px;
                        padding: 0.6rem 0.9rem;
                        margin-bottom: 0.8rem;
                        font-size: 0.85rem;
                        color: {th["muted"]};
                    '>
                        Agendando para: &nbsp;
                        <span style='color:{th["heading"]}; font-weight:600;'>
                            {st.session_state.nombre}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                with st.form("form_reserva"):
                    horario_elegido = st.selectbox(
                        "⏰ Horario de inicio",
                        horarios_libres,
                        format_func=_etiqueta_opcion
                    )
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
                            requests.post(url_slack, json=mensaje)
                        except Exception:
                            st.warning("⚠️ El break se guardó, pero falló la notificación a Slack.")

                        st.cache_data.clear()
                        st.success(f"¡Listo! Reservaste a las {horario_elegido} 🎉")
                        st.balloons()
                        time.sleep(10)
                        st.rerun()
