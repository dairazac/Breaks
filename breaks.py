import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Prueba de Conexión 🔌")

try:
    # 1. Intentamos conectar
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Intentamos leer sin especificar la pestaña (lee la primera por defecto)
    df = conn.read(ttl=10)
    
    st.success("¡CONEXIÓN EXITOSA!")
    st.dataframe(df)

except Exception as e:
    st.error("🚨 Sigue tirando error al conectar:")
    st.write(e)
