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
#  CONEXIÓN AL SHEET
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)


# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE CADA AGENTE — hoja "Agentes"
#  Columnas: Email | Nombre | Grupo | Breaks | Entrada | Salida
#    Email o Nombre: para identificar al agente (con uno alcanza;
#                    el Nombre tiene que ser igual al que usa en la app)
#    Grupo:   "Fijo", "Rotativo" o el nombre que se quiera
#             (vacío = "Rotativo"). Del mismo grupo sale uno a la vez;
#             pueden coincidir personas de grupos distintos.
#             Un nombre nuevo crea su columna en "Hoy" sola.
#    Breaks:  1 o 2 (vacío = 1). Cada break dura 30 min; los de 2 pueden
#             tomarlos en horarios distintos o seguidos.
#    Entrada / Salida: su turno (ej. 18:00 y 01:00). Si está cargado,
#             la app le marca qué horarios le convienen. No bloquea nada.
#  Si la hoja no existe o el agente no está, se usan los datos de los
#  Secrets (grupo / breaks) o los valores por defecto. Cambios: hasta 5 min.
# ─────────────────────────────────────────────
GRUPO_POR_DEFECTO = "Rotativo"
LIBRE = "Libre"


def _vacio(v):
    return v is None or str(v).strip().lower() in ("", "nan", "none", "nat")


def _a_minutos_hora(v):
    """'9', '9:00', '09:00:00', '18 hs', 0.375 (formato hora de Sheets) -> minutos."""
    if _vacio(v):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 0 <= v < 1:
            return int(round(v * 1440))
        return int(round(v * 60)) if v <= 30 else None
    if hasattr(v, "hour"):
        return v.hour * 60 + v.minute
    s = str(v).strip().lower().replace("hs", "").replace("h", "").strip()
    if " " in s:                      # "1899-12-30 09:00:00"
        s = s.split()[-1]
    try:
        partes = s.split(":")
        return int(float(partes[0])) * 60 + (int(float(partes[1])) if len(partes) > 1 and partes[1] else 0)
    except (ValueError, IndexError):
        return None


@st.cache_data(ttl=300)
def cargar_agentes():
    try:
        df = conn.read(worksheet="Agentes", ttl=300)
    except Exception:
        return {}
    df.columns = [str(c).strip().lower() for c in df.columns]
    agentes = {}
    for _, fila in df.iterrows():
        datos = {k: fila.get(k) for k in ("grupo", "breaks", "entrada", "salida")}
        email = fila.get("email")
        nom = fila.get("nombre")
        if not _vacio(email):
            agentes[("email", str(email).strip().lower())] = datos
        if not _vacio(nom):
            agentes[("nombre", str(nom).strip().lower())] = datos
    return agentes


AGENTES = cargar_agentes()


def _grupos_configurados():
    """Nombres de grupo (hoja Agentes + Secrets), sin distinguir mayúsculas."""
    canonicos = {GRUPO_POR_DEFECTO.lower(): GRUPO_POR_DEFECTO}
    valores = [d.get("grupo") for d in AGENTES.values()]
    valores += [c.get("grupo") for c in st.secrets["cuentas"].values()]
    for g in valores:
        if not _vacio(g):
            g = str(g).strip()
            canonicos.setdefault(g.lower(), g)
    return canonicos


GRUPOS = _grupos_configurados()          # {"rotativo": "Rotativo", "fijo": "Fijo", ...}


def config_agente(email, nombre_agente):
    cuenta = st.secrets["cuentas"][email]
    fila = (AGENTES.get(("email", email.strip().lower()))
            or AGENTES.get(("nombre", nombre_agente.strip().lower()))
            or {})

    def dato(clave):
        v = fila.get(clave)
        return cuenta.get(clave) if _vacio(v) else v

    g = dato("grupo")
    g = GRUPO_POR_DEFECTO if _vacio(g) else str(g).strip()
    try:
        cupo_ag = int(float(dato("breaks")))
    except (TypeError, ValueError):
        cupo_ag = 1

    entrada, salida = _a_minutos_hora(dato("entrada")), _a_minutos_hora(dato("salida"))
    franja_ag = None
    if entrada is not None and salida is not None:
        if salida <= entrada:          # turno que termina después de medianoche
            salida += 24 * 60
        franja_ag = (entrada, salida)
    return GRUPOS[g.lower()], max(1, min(cupo_ag, 4)), franja_ag


nombre = st.session_state.nombre
grupo, cupo, franja = config_agente(st.session_state.email, nombre)
col_mia = grupo


def texto_hora(m):
    return f"{(m // 60) % 24:02d}:{m % 60:02d}"


def normalizar_hoy(df):
    """Deja la hoja 'Hoy' como Horario | <una columna por grupo>.
    Si encuentra la hoja vieja (Horario | Agente), la convierte sola:
    'Agente' pasa a ser 'Rotativo' (con sus reservas) y se agregan las
    columnas de los demás grupos en Libre. Si aparece un grupo nuevo en
    los Secrets, se agrega su columna. Queda guardado con la primera reserva."""
    df = df.dropna(subset=["Horario"]).copy()
    if "Agente" in df.columns and GRUPO_POR_DEFECTO not in df.columns:
        df = df.rename(columns={"Agente": GRUPO_POR_DEFECTO})
    existentes = [c for c in df.columns
                  if c != "Horario" and not str(c).startswith("Unnamed")]
    # Grupos de los Secrets primero (en su orden) y después cualquier
    # columna que ya esté en la hoja, para no borrar reservas del día.
    columnas = list(GRUPOS.values()) + [c for c in existentes if c not in GRUPOS.values()]
    for col in columnas:
        if col not in df.columns:
            df[col] = LIBRE
        df[col] = df[col].fillna(LIBRE).astype(str).str.strip().replace("", LIBRE)
    df["Horario"] = pd.to_datetime(df["Horario"]).dt.strftime('%H:%M')
    return df[["Horario"] + columnas].reset_index(drop=True)


def grupos_en(df):
    return [c for c in df.columns if c != "Horario"]


def leer_hoy(ttl=10):
    return normalizar_hoy(conn.read(worksheet="Hoy", ttl=ttl))


df_completo = leer_hoy()


def a_minutos(hora_str):
    try:
        h, m = map(int, str(hora_str).split(':'))
        return h * 60 + m
    except Exception:
        return -1


def fin_de(hora_str, minutos=30):
    return (pd.to_datetime(hora_str, format='%H:%M') + pd.Timedelta(minutes=minutos)).strftime('%H:%M')


def breaks_de(df, quien):
    """Breaks agendados de un agente, de 30 min cada uno (2 casilleros).
    Si tomó dos seguidos (1 hora), cuenta como 2 breaks."""
    resultado = []
    for col in grupos_en(df):
        idxs = list(df.index[df[col] == quien])
        tramo = []
        for i in idxs + [None]:
            if tramo and (i is None or i != tramo[-1] + 1):
                for k in range(0, len(tramo), 2):
                    trozo = tramo[k:k + 2]
                    resultado.append({
                        "col": col,
                        "inicio": df.loc[trozo[0], "Horario"],
                        "horarios": [df.loc[j, "Horario"] for j in trozo],
                    })
                tramo = []
            if i is not None:
                tramo.append(i)
    resultado.sort(key=lambda b: a_minutos(b["inicio"]))
    return resultado


def inicios_libres(df, col):
    """Horarios donde hay 2 casilleros seguidos libres en la columna del grupo."""
    libres = []
    for i in range(len(df) - 1):
        if df.iloc[i][col] == LIBRE and df.iloc[i + 1][col] == LIBRE:
            libres.append(df.iloc[i]["Horario"])
    return libres


def reservar(quien, col, horario, cupo_max):
    """Vuelve a leer la hoja justo antes de guardar, para no pisar
    una reserva que otro agente haya hecho hace segundos."""
    df = leer_hoy(ttl=0)
    if len(breaks_de(df, quien)) >= cupo_max:
        return False, "Ya tenés todos tus breaks agendados para hoy."
    pos = list(df.index[df["Horario"] == horario])
    if not pos or pos[0] + 1 not in df.index:
        return False, "Ese horario ya no está disponible. Elegí otro."
    i = pos[0]
    if df.loc[i, col] != LIBRE or df.loc[i + 1, col] != LIBRE:
        return False, "Alguien de tu grupo acaba de tomar ese horario. Elegí otro."
    df.loc[[i, i + 1], col] = quien
    conn.update(worksheet="Hoy", data=df)
    st.cache_data.clear()
    return True, len(breaks_de(df, quien))


def liberar(quien, brk):
    df = leer_hoy(ttl=0)
    mascara = df["Horario"].isin(brk["horarios"]) & (df[brk["col"]] == quien)
    df.loc[mascara, brk["col"]] = LIBRE
    conn.update(worksheet="Hoy", data=df)
    st.cache_data.clear()


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
#  SUGERENCIA PERSONALIZADA (turno del agente + curva de demanda)
#  Nunca bloquea: solo ordena y etiqueta los horarios.
#    ⛔ Fuera de tu turno        → el break no entra completo en su franja
#    ⚠️ Última hora de tu turno  → el break toca la última hora del turno
#    🟢 Recomendado              → dentro de lo que le sirve, la menor demanda
#    🔴 Alta demanda             → mejor evitarlo si se puede
# ─────────────────────────────────────────────
def _sirve(m):
    """El break de 30 min entra en el turno y termina antes de la última hora."""
    if not franja:
        return True
    entrada, salida = franja
    return m >= entrada and m + 30 <= salida - 60


if franja and mapa_demanda:
    # Se recomienda el nivel de demanda más bajo DENTRO de su turno, pero solo
    # si en su turno hay diferencia (si todo es "Medio", no se marca nada 🟢).
    _niveles_utiles = [ORDEN_NIVEL.get(nivel_de(h), 1)
                       for h in df_completo["Horario"] if _sirve(a_minutos(h))]
    if _niveles_utiles and min(_niveles_utiles) < max(_niveles_utiles):
        NIVEL_RECOMENDADO = min(_niveles_utiles)
    elif _niveles_utiles and min(_niveles_utiles) == 0:
        NIVEL_RECOMENDADO = 0      # todo su turno es de baja demanda
    else:
        NIVEL_RECOMENDADO = None
else:
    NIVEL_RECOMENDADO = 0          # sin turno cargado: como siempre, recomendado = Bajo


def evaluar(horario):
    """(orden, etiqueta) de un horario de inicio para este agente."""
    m = a_minutos(horario)
    if franja:
        entrada, salida = franja
        if m < entrada or m + 30 > salida:
            return 4, "⛔ Fuera de tu turno"
        if m + 30 > salida - 60:
            return 3, "⚠️ Última hora de tu turno"
    if not mapa_demanda:
        return 1, ""
    nivel = ORDEN_NIVEL.get(nivel_de(horario), 1)
    if nivel == NIVEL_RECOMENDADO and nivel < 2:
        return 0, "🟢 Recomendado"
    if nivel == 2:
        return 2, "🔴 Alta demanda"
    return 1, ""


HAY_SUGERENCIAS = bool(mapa_demanda) or bool(franja)


# ─────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────
col_logo, col_saludo, col_salir = st.columns([0.15, 0.65, 0.20], vertical_alignment="center")

with col_logo:
    st.image("logo.png", width=150)

with col_saludo:
    nombre_corto = nombre.split()[0]
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
        st.caption(f"Estás en el grupo **{col_mia}** · de cada grupo sale una persona a la vez, "
                   f"y puede coincidir con alguien de otro grupo.")

        vista = st.radio(
            "Filtrar horarios:",
            ["Disponibles (A partir de ahora)", "Ver todo el día"],
            horizontal=True
        )

        df_mostrar = df_completo.copy()
        columnas_grupo = grupos_en(df_completo)

        if vista == "Disponibles (A partir de ahora)":
            tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
            ahora = datetime.now(tz_arg)
            minutos_ahora = ahora.hour * 60 + ahora.minute
            df_mostrar = df_mostrar[df_mostrar["Horario"].apply(a_minutos) >= minutos_ahora]

        tiempos = pd.to_datetime(df_mostrar["Horario"], format='%H:%M')
        tiempos_fin = (tiempos + pd.Timedelta(minutes=15)).dt.strftime('%H:%M')
        df_mostrar["Bloque"] = df_mostrar["Horario"] + " → " + tiempos_fin

        # Sugerencia personalizada (solo donde tu grupo tiene lugar)
        def _etiqueta_sugerencia(row):
            if row[col_mia] != LIBRE or not HAY_SUGERENCIAS:
                return ""
            return evaluar(row["Horario"])[1]

        df_mostrar["Sugerencia"] = df_mostrar.apply(_etiqueta_sugerencia, axis=1) if len(df_mostrar) else ""

        # Métricas rápidas (de tu grupo)
        total = len(df_mostrar)
        libres = int((df_mostrar[col_mia] == LIBRE).sum())
        ocupados = total - libres

        m1, m2, m3 = st.columns(3)
        m1.metric("Total bloques", total)
        m2.metric(f"🟢 Libres · {col_mia}", libres)
        m3.metric(f"🔴 En break · {col_mia}", ocupados)

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

        # Colores: cada columna de grupo según su propio estado;
        # Bloque y Sugerencia según el estado de tu grupo.
        ESTILO_LIBRE = ('background-color: rgba(34, 197, 94, 0.07); '
                        'color: #4ADE80; font-weight: 500')
        ESTILO_OCUPADO = ('background-color: rgba(239, 68, 68, 0.07); '
                          'color: #F87171; font-weight: 500')

        def color_fila(row):
            estilos = []
            for c in row.index:
                ref = row[c] if c in columnas_grupo else row[col_mia]
                estilos.append(ESTILO_LIBRE if ref == LIBRE else ESTILO_OCUPADO)
            return estilos

        columnas_tabla = ["Bloque"] + columnas_grupo + (["Sugerencia"] if HAY_SUGERENCIAS else [])
        st.dataframe(
            df_mostrar[columnas_tabla].style.apply(color_fila, axis=1),
            use_container_width=True,
            hide_index=True
        )

        leyenda = ["↻ Se actualiza automáticamente cada 10 segundos"]
        if mapa_demanda:
            leyenda.append("🟢 Recomendado = baja demanda esperada" + (" dentro de tu turno" if franja else ""))
            leyenda.append("🔴 Alta demanda = mejor evitarlo si se puede")
        if franja:
            leyenda.append("⚠️ = el break toca tu última hora · ⛔ = fuera de tu turno (no se bloquea, es solo una sugerencia)")
        st.caption(" · ".join(leyenda))


# ══════════════════════════════════════════════
#  COLUMNA DERECHA — Panel de acción
# ══════════════════════════════════════════════
with col_der:
    with st.container(border=True):
        st.subheader("🙋‍♂️ Mi Break")

        texto_turno = (f" · Tu turno: {texto_hora(franja[0])} a {texto_hora(franja[1])}"
                       if franja else "")
        if cupo == 1:
            st.caption(f"Grupo {col_mia} · 1 break de 30 minutos{texto_turno}")
        else:
            st.caption(f"Grupo {col_mia} · {cupo} breaks de 30 minutos — podés tomarlos "
                       f"en horarios distintos o seguidos{texto_turno}")

        # Reserva pedida con "Confirmar Break": se toma el horario exacto que
        # eligió el agente al hacer clic (aunque la lista se haya refrescado).
        pedido = st.session_state.pop("_reserva_pedida", None)
        if pedido:
            ok, resultado = reservar(nombre, col_mia, pedido, cupo)
            if not ok:
                st.error(resultado)
            else:
                try:
                    url_slack = st.secrets["slack_webhook"]
                    detalle = "" if cupo == 1 else f" ({resultado}/{cupo})"
                    mensaje = {"text": f"☕ *{nombre}* agendó su break{detalle} a las *{pedido}* hs."}
                    requests.post(url_slack, json=mensaje)
                except Exception:
                    st.warning("⚠️ El break se guardó, pero falló la notificación a Slack.")

                st.success(f"¡Listo! Reservaste a las {pedido} 🎉")
                st.balloons()
                time.sleep(10)
                st.rerun()

        mis_breaks = breaks_de(df_completo, nombre)

        for n, brk in enumerate(mis_breaks, start=1):
            titulo = "Break agendado" if cupo == 1 else f"Break {n} de {cupo}"
            # Card de estado del break
            st.markdown(f"""
                <div style='
                    background: rgba(79, 126, 255, 0.1);
                    border: 1px solid rgba(79, 126, 255, 0.25);
                    border-radius: 10px;
                    padding: 1rem 1.2rem;
                    margin-bottom: 0.6rem;
                '>
                    <div style='font-size:0.75rem; color:rgba(255,255,255,0.45);
                                text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.3rem;'>
                        {titulo}
                    </div>
                    <div style='font-size:1.6rem; font-weight:700; color:#E8EAF0; line-height:1;'>
                        {brk["inicio"]}
                    </div>
                    <div style='font-size:0.82rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;'>
                        Hasta las {fin_de(brk["inicio"])} · Duración: 30 minutos
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"🗑️ Eliminar / Liberar break de las {brk['inicio']}",
                         key=f"liberar_{brk['col']}_{brk['inicio']}",
                         use_container_width=True):
                liberar(nombre, brk)
                st.success("¡Tu break fue eliminado!")
                time.sleep(1.5)
                st.rerun()

        if len(mis_breaks) < cupo:
            if mis_breaks:
                st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

            horarios_libres = inicios_libres(df_mostrar, col_mia)

            # Ordenamos mostrando primero los sugeridos para este agente (su turno
            # y la demanda), sin restringir: puede elegir cualquier horario libre.
            if HAY_SUGERENCIAS:
                horarios_libres.sort(key=lambda h: (evaluar(h)[0], a_minutos(h)))

            def _etiqueta_opcion(h):
                etiqueta = evaluar(h)[1] if HAY_SUGERENCIAS else ""
                if not etiqueta:
                    return h
                emoji, texto = etiqueta.split(" ", 1)
                return f"{emoji} {h} · {texto}"

            if not horarios_libres:
                st.warning(f"¡No hay bloques de 30 min libres en el grupo {col_mia}!")

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
                            {nombre}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                numero = len(mis_breaks) + 1
                etiqueta_select = ("⏰ Horario de inicio" if cupo == 1
                                   else f"⏰ Horario de inicio · break {numero} de {cupo}")

                # Una clave por vista, así al cambiar de vista vuelve al primer sugerido
                clave_horario = "horario_elegido_" + ("todo" if vista == "Ver todo el día" else "ahora")

                def _pedir_reserva():
                    st.session_state["_reserva_pedida"] = st.session_state.get(clave_horario)

                with st.form("form_reserva"):
                    st.selectbox(
                        etiqueta_select,
                        horarios_libres,
                        format_func=_etiqueta_opcion,
                        key=clave_horario
                    )
                    st.caption("🔒 Se bloquearán 2 turnos de 15 min consecutivos.")
                    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                    st.form_submit_button("☕ Confirmar Break", use_container_width=True,
                                          on_click=_pedir_reserva)
