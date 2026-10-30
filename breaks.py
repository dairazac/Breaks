import base64
import html
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import pytz
from datetime import datetime
import extra_streamlit_components as stx
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Breaks · Contact Center", page_icon="☕", layout="wide")
st_autorefresh(interval=15000, key="autorefresh")

TZ_ARG = pytz.timezone('America/Argentina/Buenos_Aires')


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
#  TEMA (oscuro / claro)
#  Cada persona elige el suyo con el botón del encabezado y queda
#  guardado en una cookie de su navegador (por defecto: oscuro).
# ─────────────────────────────────────────────
if "tema" not in st.session_state:
    _tema_guardado = cookie_manager.get("fudo_tema")
    if _tema_guardado in ("oscuro", "claro"):
        st.session_state.tema = _tema_guardado

if st.session_state.pop("_guardar_tema", False):
    cookie_manager.set("fudo_tema", st.session_state.tema, key="set_tema",
                       expires_at=datetime.now() + pd.Timedelta(days=365))

TEMA = st.session_state.get("tema", "oscuro")


def _cambiar_tema():
    st.session_state.tema = "claro" if TEMA == "oscuro" else "oscuro"
    st.session_state._guardar_tema = True


# Paleta: naranja Fudo (#FF5023, el del logo) como único acento.
# Los dos temas usan los mismos nombres de variable; el CSS de abajo
# solo usa var(--...), así que cambiar un color es tocarlo acá.
PALETAS = {
    "oscuro": {
        "bg": "#0E0F11", "surface": "#16171A", "surface2": "#1D1F23",
        "line": "#2A2D33", "line2": "#353840",
        "text": "#F3F3F4", "muted": "#A6A9B1", "faint": "#8A8E97",
        "accent": "#FF5023", "accent-hover": "#FF6A40", "accent-ink": "#FF6A40",
        "accent-soft": "rgba(255,80,35,.13)", "accent-line": "rgba(255,80,35,.55)",
        "on-accent": "#1A0904",
        "free": "#3FD08A", "free-soft": "rgba(63,208,138,.07)", "free-line": "rgba(63,208,138,.28)",
        "busy": "#24262B", "busy-ink": "#B9BCC3",
        "ok-soft": "rgba(63,208,138,.10)", "err-soft": "rgba(255,92,92,.10)", "err-ink": "#FF8A8A",
        "warn-soft": "rgba(255,190,70,.10)", "warn-ink": "#FFC965",
        "shadow": "0 1px 0 rgba(255,255,255,.03) inset, 0 12px 32px rgba(0,0,0,.35)",
        "scheme": "dark",
    },
    "claro": {
        "bg": "#F5F4F1", "surface": "#FFFFFF", "surface2": "#F3F2EF",
        "line": "#E4E2DD", "line2": "#D6D3CD",
        "text": "#17181A", "muted": "#575B63", "faint": "#6B6F77",
        "accent": "#FF5023", "accent-hover": "#FF6A40", "accent-ink": "#C2370A",
        "accent-soft": "rgba(255,80,35,.10)", "accent-line": "rgba(255,80,35,.60)",
        "on-accent": "#1A0904",
        "free": "#0F7A47", "free-soft": "rgba(15,122,71,.06)", "free-line": "rgba(15,122,71,.30)",
        "busy": "#ECEAE6", "busy-ink": "#4A4E56",
        "ok-soft": "rgba(15,122,71,.08)", "err-soft": "rgba(200,40,40,.07)", "err-ink": "#B42318",
        "warn-soft": "rgba(200,130,0,.09)", "warn-ink": "#8A5A00",
        "shadow": "0 1px 2px rgba(20,20,20,.04), 0 8px 24px rgba(20,20,20,.06)",
        "scheme": "light",
    },
}


def _variables_css(tema):
    p = PALETAS[tema]
    variables = "".join(f"--{k}:{v};" for k, v in p.items() if k != "scheme")
    return f":root{{{variables}color-scheme:{p['scheme']};}}"


# ─────────────────────────────────────────────
#  CSS GLOBAL
# ─────────────────────────────────────────────
FUENTE = "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');"

CSS = """
/* ── Base ── */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--bg) !important;
    color: var(--text);
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}
.stApp p, .stApp label, .stApp input, .stApp button, .stApp li,
.stApp h1, .stApp h2, .stApp h3 {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
}
[data-testid="stMarkdownContainer"] { color: var(--text); }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1280px !important;
    padding: 1.4rem 2rem 3.5rem !important;
}
[data-testid="stHorizontalBlock"] { gap: 1.5rem; }
[data-testid="stElementContainer"]:has(> .stHtml:empty),
[data-testid="stElementContainer"]:has(iframe[height="0"]) { display: none; }

/* ── Tarjetas (contenedores con key) ── */
.st-key-panel_disp, .st-key-panel_mibreak, .st-key-login_card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    box-shadow: var(--shadow);
    padding: 24px;
    gap: 0.9rem;
}
.st-key-login_card { padding: 36px; }
[class*="st-key-brk_"] {
    background: var(--accent-soft);
    border: 1px solid var(--accent-line);
    border-radius: 14px;
    padding: 16px 18px;
    gap: 0.75rem;
}
.st-key-pendiente {
    border: 1px dashed var(--line2);
    border-radius: 14px;
    padding: 16px 18px;
    gap: 0.6rem;
}
.st-key-barra_superior {
    border-bottom: 1px solid var(--line);
    padding-bottom: 14px;
}

/* ── Botones ── */
.stApp button[data-testid^="stBaseButton"] {
    border-radius: 11px !important;
    font-weight: 700 !important;
    min-height: 42px;
    transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.stApp button[data-testid^="stBaseButton-primary"] {
    background: var(--accent) !important;
    border: 0 !important;
    color: var(--on-accent) !important;
    font-weight: 800 !important;
    min-height: 46px;
}
.stApp button[data-testid^="stBaseButton-primary"]:hover {
    background: var(--accent-hover) !important;
}
.stApp button[data-testid^="stBaseButton-primary"] p { font-size: 15px !important; color: var(--on-accent) !important; }
.stApp button[data-testid^="stBaseButton-secondary"] {
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    color: var(--muted) !important;
}
.stApp button[data-testid^="stBaseButton-secondary"]:hover {
    border-color: var(--line2) !important;
    color: var(--text) !important;
}
.stApp button[data-testid^="stBaseButton-secondary"] p { font-size: 13px !important; }
.stApp button[data-testid^="stBaseButton"]:focus-visible {
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
    outline: 2px solid var(--accent) !important;
}

/* ── Selector "Desde ahora / Todo el día" ── */
[data-testid="stButtonGroup"] [role="radiogroup"] {
    background: var(--surface2);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 4px;
    gap: 4px !important;
    width: fit-content;
}
.stApp button[data-variant="segmented_control"] {
    background: transparent !important;
    border: 0 !important;
    border-radius: 9px !important;
    color: var(--muted) !important;
    min-height: 34px !important;
    padding: 0 14px !important;
    box-shadow: none !important;
    outline: none;
}
.stApp button[data-variant="segmented_control"][aria-checked="true"] {
    background: var(--surface) !important;
    color: var(--text) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.22) !important;
}
.stApp button[data-variant="segmented_control"]:focus-visible { outline: 2px solid var(--accent) !important; }
.stApp button[data-variant="segmented_control"] p {
    font-size: 13px !important; font-weight: 600 !important; color: inherit !important;
}
.st-key-vista [data-testid="stButtonGroup"] { display: flex; justify-content: flex-end; }

/* ── Inputs y selectores ── */
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--text) !important;
}
[data-testid="stSelectbox"] [role="group"], [data-testid="stTextInputRootElement"] {
    background: var(--surface2) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 10px !important;
    min-height: 44px;
}
[data-testid="stSelectbox"] [role="group"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
[data-testid="stSelectbox"] input, [data-testid="stTextInputRootElement"] input {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    background: transparent !important;
    font-size: 15px !important;
}
[data-testid="stSelectbox"] input { font-weight: 700 !important; font-variant-numeric: tabular-nums; cursor: pointer; }
[data-testid="stTextInputRootElement"] input::placeholder {
    color: var(--faint) !important; -webkit-text-fill-color: var(--faint) !important;
}
[data-testid="stSelectbox"] svg, [data-testid="stTextInputRootElement"] svg,
[data-testid="stTextInputRootElement"] button { color: var(--muted) !important; background: transparent !important; }
[data-testid="stSelectboxVirtualDropdown"] {
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
    background: var(--surface2) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
    background: var(--accent-soft) !important;
    color: var(--accent-ink) !important;
}
[data-testid="InputInstructions"] { display: none !important; }
[data-testid="stForm"] { border: 0 !important; padding: 0 !important; background: transparent !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: var(--muted) !important;
    font-size: 12px !important;
}

/* ── Avisos ── */
[data-testid="stAlert"] > div { border-radius: 12px !important; }
[data-testid="stAlertContentSuccess"] { color: var(--free) !important; }
[data-testid="stAlertContentError"] { color: var(--err-ink) !important; }
[data-testid="stAlertContentWarning"] { color: var(--warn-ink) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) > div { background: var(--ok-soft) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) > div { background: var(--err-soft) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) > div { background: var(--warn-soft) !important; }

/* ── Piezas propias (HTML) ── */
[data-testid="stMarkdownContainer"]:has(> .bk) { margin-bottom: 0 !important; }
.bk p { margin-bottom: 0; }
.bk-marca { display:flex; align-items:center; gap:16px; }
.bk-marca img { height:24px; width:auto; display:block; }
.bk-marca .sep { width:1px; height:26px; background:var(--line2); }
.bk-marca .titulo { display:flex; flex-direction:column; line-height:1.2; }
.bk-marca .titulo b { font-weight:700; font-size:15px; letter-spacing:-.01em; color:var(--text); }
.bk-marca .titulo span { font-size:12px; color:var(--muted); }
.bk-chip { display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:999px;
    background:var(--surface2); color:var(--muted); font-size:12px; font-weight:600; white-space:nowrap; }
.bk-chip .vivo { width:7px; height:7px; border-radius:50%; background:var(--free); box-shadow:0 0 0 3px var(--free-soft); }
.bk-user { display:flex; align-items:center; justify-content:flex-end; gap:10px; }
.bk-user .av { width:32px; height:32px; border-radius:8px; background:var(--accent-soft); color:var(--accent-ink);
    display:inline-flex; align-items:center; justify-content:center; font-weight:800; font-size:12px; flex:none; }
.bk-user .nom { font-weight:600; font-size:13px; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.bk-hero { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:16px; margin:14px 0 10px; }
.stApp .bk-hero .fecha { margin:0 0 6px !important; font-size:13px !important; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }
.stApp .bk-hero h1 { margin:0 !important; padding:0 !important; font-size:34px; line-height:1.1; font-weight:800; letter-spacing:-.03em; color:var(--text); }
.stApp .bk-hero .sub { margin:8px 0 0 !important; font-size:15px !important; color:var(--muted); }
.bk-hero .sub strong { color:var(--text); font-weight:700; }
.bk-ahora { display:inline-flex; align-items:center; gap:10px; padding:10px 14px; border-radius:12px;
    background:var(--surface); border:1px solid var(--line); color:var(--muted); font-size:13px; }
.bk-ahora b { font-weight:800; font-size:18px; color:var(--text); font-variant-numeric:tabular-nums; letter-spacing:-.02em; }

.stApp .bk-h2 { margin:0 !important; padding:0 !important; font-size:18px !important; line-height:1.3 !important; font-weight:700 !important; letter-spacing:-.01em; color:var(--text); }
.stApp .bk-h2-sub { margin:2px 0 0 !important; font-size:13px !important; line-height:1.45 !important; color:var(--muted); }

.bk-stats { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; }
.bk-stat { padding:14px 16px; border-radius:12px; background:var(--surface2); }
.bk-stat .k { font-size:12px; font-weight:600; color:var(--muted); display:flex; align-items:center; gap:6px; }
.bk-stat .k i { width:8px; height:8px; border-radius:50%; display:inline-block; }
.bk-stat .v { font-size:26px; font-weight:800; letter-spacing:-.03em; font-variant-numeric:tabular-nums; margin-top:2px; color:var(--text); }
.bk-stat.mio { background:var(--accent-soft); }
.bk-stat.mio .k, .bk-stat.mio .v { color:var(--accent-ink); }

.bk-grilla { display:flex; flex-direction:column; gap:6px; }
.bk-fila { display:grid; grid-template-columns:44px repeat(4, minmax(0,1fr)); gap:6px; }
.bk-fila .hora { display:flex; align-items:center; font-size:12px; font-weight:700; color:var(--faint); font-variant-numeric:tabular-nums; }
.bk-cel { display:flex; flex-direction:column; gap:2px; padding:9px 12px; border-radius:10px;
    border:1px solid var(--line); background:var(--surface); min-width:0; }
.bk-cel .t { font-size:13px; font-weight:700; font-variant-numeric:tabular-nums; color:var(--text); letter-spacing:-.01em; }
.bk-cel .l { font-size:12px; font-weight:500; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    display:flex; align-items:center; gap:6px; }
.bk-cel .l i { width:7px; height:7px; border-radius:50%; background:currentColor; flex:none; }
.bk-cel.libre { background:var(--free-soft); border-color:var(--free-line); }
.bk-cel.libre .l { color:var(--free); font-weight:600; }
.bk-cel.libre.evitar { background:var(--surface); border-color:var(--line); }
.bk-cel.libre.evitar .l { color:var(--muted); font-weight:500; }
.bk-cel.libre.reco { border-color:var(--free); }
.bk-cel.ocupado { background:var(--busy); border-color:transparent; }
.bk-cel.ocupado .t, .bk-cel.ocupado .l { color:var(--busy-ink); }
.bk-cel.mio { background:var(--accent-soft); border-color:var(--accent-line); }
.bk-cel.mio .t, .bk-cel.mio .l { color:var(--accent-ink); }
.bk-cel.mio .l { font-weight:700; }
.bk-cel.pasado { opacity:.42; }
.bk-cel.ahora { box-shadow:0 0 0 2px var(--text); }
.bk-cel.vacia { visibility:hidden; }
.bk-vacio { padding:28px; text-align:center; color:var(--muted); border:1px dashed var(--line2); border-radius:12px; }

.bk-leyenda { display:flex; flex-wrap:wrap; gap:8px 18px; padding-top:16px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }
.bk-leyenda span { display:inline-flex; align-items:center; gap:7px; }
.bk-leyenda i { width:14px; height:14px; border-radius:4px; display:inline-block; }

.bk-mb-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.bk-pill { font-size:12px; font-weight:700; color:var(--accent-ink); background:var(--accent-soft); padding:4px 10px; border-radius:999px; white-space:nowrap; }
.bk-progreso { display:grid; gap:6px; margin-top:14px; }
.bk-progreso div { height:6px; border-radius:99px; background:var(--surface2); border:1px solid var(--line); }
.bk-progreso div.ok { background:var(--accent); border-color:var(--accent); }
.bk-turno { margin:10px 0 0; font-size:12px; color:var(--muted); }

.bk-brk-top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.bk-etq { font-size:11px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--accent-ink); }
.bk-etq.gris { color:var(--muted); }
.bk-cuenta { display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600; color:var(--text); }
.bk-cuenta.gris { color:var(--faint); }
.bk-hora-grande { display:flex; align-items:baseline; gap:8px; margin-top:8px; }
.bk-hora-grande b { font-size:36px; font-weight:800; letter-spacing:-.04em; font-variant-numeric:tabular-nums; line-height:1; color:var(--text); }
.bk-hora-grande span { font-size:16px; font-weight:600; color:var(--muted); font-variant-numeric:tabular-nums; }

.bk-nota { display:flex; gap:12px; align-items:flex-start; padding:14px 16px; border-radius:14px; background:var(--surface2);
    border:1px solid var(--line); font-size:12px; color:var(--muted); margin-top:16px; }
.bk-nota svg { flex:none; margin-top:1px; }

.bk-login-logo img { height:28px; width:auto; display:block; }
.stApp .bk-login h1 { margin:24px 0 6px !important; padding:0 !important; font-size:26px; font-weight:800; letter-spacing:-.03em; line-height:1.15; color:var(--text); }
.stApp .bk-login p { margin:0 0 6px !important; font-size:14px !important; color:var(--muted); }
.bk-login-pie { display:flex; align-items:center; gap:8px; padding-top:16px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }

@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"], .block-container { padding: 1rem 1rem 3rem !important; }
    .bk-hero h1 { font-size:28px; }
    .bk-fila { grid-template-columns:34px repeat(4, minmax(0,1fr)); gap:4px; }
    .bk-cel { padding:7px 7px; }
    .bk-cel .l { font-size:11px; }
    .bk-cel .l i { display:none; }
    .st-key-panel_disp, .st-key-panel_mibreak { padding:16px; }
    .bk-stat { padding:10px 12px; }
    .bk-stat .v { font-size:22px; }
}
"""

st.markdown(f"<style>{FUENTE}{_variables_css(TEMA)}{CSS}</style>", unsafe_allow_html=True)


def _h(texto):
    """HTML en una sola línea: st.markdown toma las líneas con sangría
    como bloque de código y las líneas en blanco cortan el HTML."""
    return " ".join(linea.strip() for linea in texto.splitlines() if linea.strip())


def pintar(texto, width="stretch"):
    st.markdown(f"<div class='bk'>{_h(texto)}</div>", unsafe_allow_html=True,
                width=width, anchors=False)


@st.cache_data
def logo_html(clase=""):
    with open("logo.png", "rb") as f:
        datos = base64.b64encode(f.read()).decode()
    return f"<img src='data:image/png;base64,{datos}' alt='FUDO' class='{clase}'>"


ICONOS = {
    "reloj": "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/></svg>",
    "reloj18": "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/></svg>",
    "info": "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='9'/><path d='M12 8h.01M11 12h1v4h1'/></svg>",
    "candado": "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><rect x='4' y='11' width='16' height='10' rx='2'/><path d='M8 11V7a4 4 0 0 1 8 0v4'/></svg>",
}

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ─────────────────────────────────────────────
#  PANTALLA DE LOGIN
# ─────────────────────────────────────────────
if not st.session_state.logueado:

    _, col_centro, _ = st.columns([1, 1.1, 1])

    with col_centro:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        with st.container(key="login_card"):
            pintar(f"""
                <div class='bk-login'>
                    <div class='bk-login-logo'>{logo_html()}</div>
                    <h1>Agendá tu break</h1>
                    <p>Ingresá con tu email de FUDO y tu PIN.</p>
                </div>
            """)

            with st.form("login_form", border=False):
                email = st.text_input("Email corporativo", placeholder="nombre@fu.do").strip().lower()
                password = st.text_input("Contraseña o PIN", type="password", placeholder="••••••")
                submit = st.form_submit_button("Ingresar", type="primary",
                                               icon=":material/arrow_forward:", width="stretch")

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

            pintar(f"""
                <div class='bk-login-pie'>{ICONOS['candado']}
                Tu sesión queda activa por 60 días en este navegador.</div>
            """)
        pintar("<p style='text-align:center; margin-top:20px; font-size:12px; color:var(--faint);'>Contact Center · Breaks</p>")
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
#  Secrets (grupo / breaks) o los valores por defecto. Cambios: hasta 1 min.
#  Ojo: si a alguien se le cambia el grupo con breaks ya agendados ese día,
#  esos breaks quedan en la columna del grupo viejo. La app se los sigue
#  mostrando (tabla y "Mi Break"), pero conviene que los libere y reagende.
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


@st.cache_data(ttl=60)
def _leer_agentes():
    """None si la lectura falló (se reintenta al minuto)."""
    try:
        df = conn.read(worksheet="Agentes", ttl=60)
    except Exception:
        return None
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


def cargar_agentes():
    """Si falla la lectura de la hoja (ej. límite de Google), se sigue usando
    la última configuración buena en vez de mandar al agente al grupo por
    defecto: así un fallo momentáneo no le cambia la columna donde reserva."""
    agentes = _leer_agentes()
    if agentes is None:
        return st.session_state.get("_agentes_ok", {})
    st.session_state["_agentes_ok"] = agentes
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


def horarios_de(df, quien):
    """Casilleros que el agente tiene tomados, en cualquier columna."""
    cols = grupos_en(df)
    if not cols:
        return set()
    return set(df.loc[(df[cols] == quien).any(axis=1), "Horario"])


def inicios_libres(df, col, propios=frozenset()):
    """Horarios donde hay 2 casilleros seguidos libres en la columna del grupo
    (y que no se pisan con un break que el agente ya tiene)."""
    libres = []
    for i in range(len(df) - 1):
        h1, h2 = df.iloc[i]["Horario"], df.iloc[i + 1]["Horario"]
        if (df.iloc[i][col] == LIBRE and df.iloc[i + 1][col] == LIBRE
                and h1 not in propios and h2 not in propios):
            libres.append(h1)
    return libres


def unir_horarios(horarios):
    horarios = list(horarios)
    if len(horarios) <= 1:
        return "".join(horarios)
    return ", ".join(horarios[:-1]) + " y " + horarios[-1]


def reservar(quien, col, horarios, cupo_max):
    """Reserva uno o varios breaks de una sola vez (todo o nada).
    Vuelve a leer la hoja justo antes de guardar, para no pisar
    una reserva que otro agente haya hecho hace segundos."""
    horarios = sorted(horarios, key=a_minutos)
    df = leer_hoy(ttl=0)
    restantes = cupo_max - len(breaks_de(df, quien))
    if restantes <= 0:
        return False, "Ya tenés todos tus breaks agendados para hoy."
    if len(horarios) > restantes:
        return False, (f"Te queda{'n' if restantes > 1 else ''} {restantes} "
                       f"break{'s' if restantes > 1 else ''} por agendar. Elegí de nuevo.")
    propios = horarios_de(df, quien)
    filas = []
    for h in horarios:
        pos = list(df.index[df["Horario"] == h])
        if not pos or pos[0] + 1 not in df.index:
            return False, f"El horario de las {h} ya no está disponible. No se guardó nada: elegí de nuevo."
        i = pos[0]
        for j in (i, i + 1):
            if j in filas:
                return False, ("Los horarios que elegiste se pisan entre sí. Cada break dura "
                               "30 min: si los querés seguidos, elegí por ejemplo "
                               f"{horarios[0]} y {fin_de(horarios[0])}.")
            if df.loc[j, "Horario"] in propios:
                return False, f"Ya tenés un break que se pisa con el de las {h}."
            if df.loc[j, col] != LIBRE:
                return False, (f"Alguien acaba de tomar el horario de las {h}. "
                               "No se guardó nada: elegí de nuevo.")
        filas += [i, i + 1]
    df.loc[filas, col] = quien
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


# ─────────────────────────────────────────────
#  INTERRUPTOR DE SUGERENCIAS
#  Para apagarlas, agregar en los Secrets (arriba de todo, fuera de
#  [cuentas]) la línea:   sugerencias = false
#  Apagadas, la app se ve como la versión original: sin columna
#  "Sugerencia", horarios en orden y sin etiquetas. Para prenderlas,
#  borrar la línea o poner  sugerencias = true
# ─────────────────────────────────────────────
SUGERENCIAS_ACTIVADAS = str(st.secrets.get("sugerencias", True)).strip().lower() not in ("false", "0", "no", "off")
HAY_SUGERENCIAS = SUGERENCIAS_ACTIVADAS and (bool(mapa_demanda) or bool(franja))



# ─────────────────────────────────────────────
#  HORA ACTUAL Y DATOS DEL AGENTE PARA LA PANTALLA
# ─────────────────────────────────────────────
ahora_dt = datetime.now(TZ_ARG)
minutos_ahora = ahora_dt.hour * 60 + ahora_dt.minute
mis_horarios = horarios_de(df_completo, nombre)
mis_breaks = breaks_de(df_completo, nombre)


def _duracion(minutos):
    if minutos < 60:
        return f"{minutos} min"
    h, r = divmod(minutos, 60)
    return f"{h} h {r:02d} min" if r else f"{h} h"


def cuenta_regresiva(inicio):
    """('Empieza en 33 min', '') / ('En curso · …', '') / ('Ya terminó', 'gris')."""
    ahora = minutos_ahora + (24 * 60 if minutos_ahora < 6 * 60 else 0)   # madrugada
    falta = a_minutos(inicio) - ahora
    if falta > 0:
        return f"Empieza en {_duracion(falta)}", ""
    if falta > -30:
        return f"En curso · termina en {_duracion(30 + falta)}", ""
    return "Ya terminó", "gris"


# ─────────────────────────────────────────────
#  ENCABEZADO
# ─────────────────────────────────────────────
with st.container(key="barra_superior", horizontal=True, horizontal_alignment="distribute",
                  vertical_alignment="center", gap="small"):
    pintar(f"""
        <div class='bk-marca'>{logo_html()}<div class='sep'></div>
        <div class='titulo'><b>Breaks</b><span>Contact Center</span></div></div>
    """, width="content")

    with st.container(horizontal=True, width="content", vertical_alignment="center", gap="small"):
        pintar("<span class='bk-chip'><span class='vivo'></span>En vivo · se actualiza cada 15 s</span>",
               width="content")
        st.button("Claro" if TEMA == "oscuro" else "Oscuro",
                  icon=":material/light_mode:" if TEMA == "oscuro" else ":material/dark_mode:",
                  help="Cambiar a modo claro" if TEMA == "oscuro" else "Cambiar a modo oscuro",
                  on_click=_cambiar_tema, key="btn_tema")
        iniciales = "".join(p[0] for p in nombre.replace(".", " ").split()[:2]).upper()
        pintar(f"""
            <div class='bk-user'><span class='av'>{html.escape(iniciales)}</span>
            <span class='nom'>{html.escape(nombre)}</span></div>
        """, width="content")
        if st.button("Salir", icon=":material/logout:", key="btn_salir"):
            cookie_manager.delete('fudo_user_email')
            st.session_state.logueado = False
            st.session_state.ignorar_cookie = True # Prendemos el escudo antes de reiniciar
            st.rerun()


# ─────────────────────────────────────────────
#  SALUDO
# ─────────────────────────────────────────────
nombre_corto = nombre.split()[0]
fecha_txt = f"{DIAS[ahora_dt.weekday()]} {ahora_dt.day} de {MESES[ahora_dt.month - 1]}"
if cupo == 1:
    sub_txt = "Hoy tenés <strong>1 break de 30 minutos</strong>."
else:
    sub_txt = (f"Hoy tenés <strong>{cupo} breaks de 30 minutos</strong>. "
               "Podés tomarlos separados o seguidos.")
if franja and SUGERENCIAS_ACTIVADAS:
    sub_txt += f" Tu turno: {texto_hora(franja[0])} a {texto_hora(franja[1])}."

pintar(f"""
    <div class='bk-hero'>
        <div>
            <p class='fecha'>{fecha_txt}</p>
            <h1>Hola, {html.escape(nombre_corto)}</h1>
            <p class='sub'>{sub_txt}</p>
        </div>
        <div class='bk-ahora'>{ICONOS['reloj18']}Ahora <b>{ahora_dt.strftime('%H:%M')}</b></div>
    </div>
""")


# ─────────────────────────────────────────────
#  GRILLA DE DISPONIBILIDAD (HTML)
#  Una fila por hora y 4 bloques de 15 min. Solo muestra:
#  para reservar se usa el formulario de "Mi break".
# ─────────────────────────────────────────────
ETIQUETA_SUGERENCIA = {2: "Alta demanda", 3: "Última hora", 4: "Fuera de turno"}


def html_grilla(df, desde_ahora):
    filas = {}
    for _, fila in df.iterrows():
        h = fila["Horario"]
        m = a_minutos(h)
        if m < 0 or (desde_ahora and m // 60 < minutos_ahora // 60):
            continue
        quien = nombre if h in mis_horarios else fila[col_mia]
        if quien == nombre:
            clase, texto = "mio", "Tu break"
        elif quien == LIBRE:
            clase, texto = "libre", "Libre"
        else:
            clase, texto = "ocupado", quien
        pasado = m + 15 <= minutos_ahora
        if clase == "libre" and not pasado and HAY_SUGERENCIAS:
            orden, etiqueta = evaluar(h)
            if orden == 0 and etiqueta:
                clase, texto = "libre reco", "Recomendado"
            elif orden in ETIQUETA_SUGERENCIA:
                clase, texto = "libre evitar", ETIQUETA_SUGERENCIA[orden]
        if pasado:
            clase += " pasado"
        elif m <= minutos_ahora < m + 15:
            clase += " ahora"
        texto = html.escape(str(texto))
        celda = (f"<div class='bk-cel {clase}' title='{h} · {texto}'>"
                 f"<span class='t'>{h}</span><span class='l'><i></i>{texto}</span></div>")
        filas.setdefault(m // 60, {})[(m % 60) // 15] = celda

    if not filas:
        return "<div class='bk-vacio'>No quedan bloques por hoy.</div>"
    partes = ["<div class='bk-grilla'>"]
    for hora in sorted(filas):
        celdas = "".join(filas[hora].get(q, "<div class='bk-cel vacia'></div>") for q in range(4))
        partes.append(f"<div class='bk-fila'><div class='hora'>{hora % 24:02d}h</div>{celdas}</div>")
    partes.append("</div>")
    return "".join(partes)


# ─────────────────────────────────────────────
#  COLUMNAS PRINCIPALES
# ─────────────────────────────────────────────
col_izq, col_der = st.columns([0.62, 0.38], gap="large")


# ══════════════════════════════════════════════
#  COLUMNA IZQUIERDA — Tablero de disponibilidad
# ══════════════════════════════════════════════
VISTAS = ["Desde ahora", "Todo el día"]


def _fijar_vista():
    # Si se toca la opción ya elegida, el control queda vacío: se vuelve a la anterior.
    if st.session_state.vista is None:
        st.session_state.vista = st.session_state.get("_vista_anterior", VISTAS[0])
    st.session_state._vista_anterior = st.session_state.vista


with col_izq:
    with st.container(key="panel_disp"):
        c_tit, c_filtro = st.columns([0.58, 0.42], vertical_alignment="center")
        with c_tit:
            pintar("""
                <h2 class='bk-h2'>Disponibilidad de hoy</h2>
                <p class='bk-h2-sub'>Bloques de 15 minutos · cada break ocupa 2 bloques</p>
            """)
        with c_filtro:
            vista = st.segmented_control("Filtrar horarios", VISTAS, default=VISTAS[0],
                                         key="vista", on_change=_fijar_vista,
                                         label_visibility="collapsed") or VISTAS[0]
        desde_ahora = vista == VISTAS[0]

        df_mostrar = df_completo.copy()
        if desde_ahora:
            df_mostrar = df_mostrar[df_mostrar["Horario"].apply(a_minutos) >= minutos_ahora]

        # El agente ve solo la disponibilidad de su grupo (los grupos no se
        # muestran en la app). Sus propios breaks se muestran siempre, estén
        # en la columna que estén (ej. si le cambiaron el grupo).
        df_mostrar["Agente"] = df_mostrar[col_mia]
        df_mostrar.loc[df_mostrar["Horario"].isin(mis_horarios), "Agente"] = nombre

        libres = int((df_mostrar["Agente"] == LIBRE).sum())
        ocupados = int(((df_mostrar["Agente"] != LIBRE) & (df_mostrar["Agente"] != nombre)).sum())

        pintar(f"""
            <div class='bk-stats'>
                <div class='bk-stat'><div class='k'><i style='background:var(--free)'></i>Bloques libres</div><div class='v'>{libres}</div></div>
                <div class='bk-stat'><div class='k'><i style='background:var(--busy-ink)'></i>Ocupados</div><div class='v'>{ocupados}</div></div>
                <div class='bk-stat mio'><div class='k'><i style='background:var(--accent)'></i>Tus breaks</div><div class='v'>{len(mis_breaks)}/{cupo}</div></div>
            </div>
        """)

        pintar(html_grilla(df_completo, desde_ahora))

        leyenda = [
            "<span><i style='background:var(--free-soft); border:1px solid var(--free-line)'></i>Libre</span>",
            "<span><i style='background:var(--busy)'></i>Ocupado</span>",
            "<span><i style='background:var(--accent-soft); border:1px solid var(--accent-line)'></i>Tu break</span>",
            "<span><i style='border:1px solid var(--line); box-shadow:0 0 0 2px var(--text) inset'></i>Bloque actual</span>",
            "<span><i style='background:var(--busy); border:1px solid var(--line2); opacity:.45'></i>Ya pasó</span>",
        ]
        if HAY_SUGERENCIAS:
            leyenda.append("<span><i style='background:var(--free-soft); border:1px solid var(--free)'></i>"
                           "Recomendado</span>")
            leyenda.append("<span><i style='background:var(--surface); border:1px solid var(--line)'></i>"
                           "Mejor evitar (alta demanda, tu última hora o fuera de turno · no se bloquea)</span>")
        pintar(f"<div class='bk-leyenda'>{''.join(leyenda)}</div>")


# ══════════════════════════════════════════════
#  COLUMNA DERECHA — Mi break
# ══════════════════════════════════════════════
with col_der:
    with st.container(key="panel_mibreak"):
        if cupo == 1:
            estado = "Agendado" if mis_breaks else "Sin agendar"
        else:
            estado = f"{len(mis_breaks)} de {cupo} agendados"
        barras = "".join("<div class='ok'></div>" if i < len(mis_breaks) else "<div></div>"
                         for i in range(cupo))
        pintar(f"""
            <div class='bk-mb-head'><h2 class='bk-h2'>Mi break</h2><span class='bk-pill'>{estado}</span></div>
            <div class='bk-progreso' style='grid-template-columns:repeat({cupo}, minmax(0,1fr))'>{barras}</div>
        """)

        # Reserva pedida con "Confirmar": se toma el horario exacto que
        # eligió el agente al hacer clic (aunque la lista se haya refrescado).
        pedido = st.session_state.pop("_reserva_pedida", None)
        if pedido:
            ok, resultado = reservar(nombre, col_mia, pedido, cupo)
            if not ok:
                st.error(resultado)
            else:
                pedido = sorted(pedido, key=a_minutos)
                texto = unir_horarios(pedido)
                try:
                    url_slack = st.secrets["slack_webhook"]
                    if len(pedido) > 1:
                        detalle = "" if resultado == len(pedido) else f" ({resultado}/{cupo})"
                        horas = unir_horarios([f"*{h}*" for h in pedido])
                        mensaje = {"text": f"☕ *{nombre}* agendó sus breaks{detalle} a las {horas} hs."}
                    else:
                        detalle = "" if cupo == 1 else f" ({resultado}/{cupo})"
                        mensaje = {"text": f"☕ *{nombre}* agendó su break{detalle} a las *{texto}* hs."}
                    requests.post(url_slack, json=mensaje)
                except Exception:
                    st.warning("El break se guardó, pero falló la notificación a Slack.")

                st.success(f"¡Listo! Reservaste a las {texto} 🎉")
                st.balloons()
                time.sleep(10)
                st.rerun()

        # Breaks ya agendados
        for n, brk in enumerate(mis_breaks, start=1):
            titulo = "Tu break" if cupo == 1 else f"Break {n}"
            cuenta, tono = cuenta_regresiva(brk["inicio"])
            with st.container(key=f"brk_{n}"):
                pintar(f"""
                    <div class='bk-brk-top'>
                        <span class='bk-etq'>{titulo}</span>
                        <span class='bk-cuenta {tono}'>{ICONOS['reloj']}{cuenta}</span>
                    </div>
                    <div class='bk-hora-grande'><b>{brk["inicio"]}</b><span>→ {fin_de(brk["inicio"])}</span></div>
                """)
                if st.button("Liberar este horario", icon=":material/delete:",
                             key=f"liberar_{brk['col']}_{brk['inicio']}", width="stretch"):
                    liberar(nombre, brk)
                    st.success("¡Tu break fue eliminado!")
                    time.sleep(1.5)
                    st.rerun()

        # Breaks por agendar
        if len(mis_breaks) < cupo:
            restantes = cupo - len(mis_breaks)
            horarios_libres = inicios_libres(df_mostrar, col_mia, mis_horarios)

            # Primero los sugeridos para este agente (su turno y la demanda),
            # sin restringir: puede elegir cualquier horario libre.
            if HAY_SUGERENCIAS:
                horarios_libres.sort(key=lambda h: (evaluar(h)[0], a_minutos(h)))

            def _etiqueta_opcion(h):
                etiqueta = evaluar(h)[1] if HAY_SUGERENCIAS else ""
                if not etiqueta:
                    return h
                emoji, texto = etiqueta.split(" ", 1)
                return f"{emoji} {h} · {texto}"

            with st.container(key="pendiente"):
                if cupo == 1:
                    titulo_pend = "Tu break"
                elif restantes == 1:
                    titulo_pend = f"Break {cupo}"
                else:
                    titulo_pend = "Tus breaks"
                pintar(f"""
                    <div class='bk-brk-top'>
                        <span class='bk-etq gris'>{titulo_pend}</span>
                        <span class='bk-cuenta gris'>Sin agendar</span>
                    </div>
                """)

                if not horarios_libres:
                    st.warning("No quedan bloques de 30 min libres.")
                else:
                    # Un selector por cada break que le falta agendar: el primero
                    # es obligatorio y los demás opcionales ("Lo agendo más tarde"),
                    # así puede confirmar todos juntos o de a uno.
                    SIN_ELEGIR = "__despues__"

                    def _etiqueta_opcion_o_despues(h):
                        return "— Lo agendo más tarde —" if h == SIN_ELEGIR else _etiqueta_opcion(h)

                    # Una clave por vista, así al cambiar de vista vuelve al primer sugerido
                    sufijo = "ahora" if desde_ahora else "todo"
                    claves = [f"horario_elegido_{k}_{sufijo}" for k in range(restantes)]

                    def _pedir_reserva():
                        elegidos = [st.session_state.get(c) for c in claves]
                        st.session_state["_reserva_pedida"] = [h for h in elegidos
                                                               if h and h != SIN_ELEGIR]

                    with st.form("form_reserva", border=False):
                        for k, clave in enumerate(claves):
                            numero = len(mis_breaks) + 1 + k
                            if cupo == 1 or restantes == 1:
                                etiqueta_select = "Horario de inicio"
                            else:
                                etiqueta_select = f"Break {numero} de {cupo}" + (" (opcional)" if k else "")
                            st.selectbox(
                                etiqueta_select,
                                horarios_libres if k == 0 else [SIN_ELEGIR] + horarios_libres,
                                format_func=_etiqueta_opcion_o_despues,
                                key=clave
                            )
                        if restantes > 1:
                            st.caption("Cada break bloquea 2 turnos de 15 min. Podés confirmar "
                                       "todos juntos o dejar alguno para más tarde. Para tomarlos "
                                       "seguidos, elegí horarios separados por 30 min (ej. 19:00 y 19:30).")
                        elif mis_breaks:
                            st.caption("Se bloquean 2 turnos de 15 min. Para tomarlo seguido al "
                                       f"anterior, elegí {fin_de(mis_breaks[-1]['inicio'])}.")
                        else:
                            st.caption("Se bloquean 2 turnos de 15 min consecutivos.")
                        st.form_submit_button("Confirmar breaks" if restantes > 1 else "Confirmar break",
                                              type="primary", icon=":material/check:",
                                              width="stretch", on_click=_pedir_reserva)

    pintar(f"""
        <div class='bk-nota'>{ICONOS['info']}
        <span>Cuando confirmás, el equipo recibe el aviso en Slack. Si cambiás de idea,
        liberá el horario para que lo use otra persona.</span></div>
    """)
