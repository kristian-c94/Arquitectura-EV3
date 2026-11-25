import streamlit as st
import requests
import pandas as pd

import os
import streamlit as st
import requests
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADERS = {"x-api-key": "pagoseguro-secret-2026"}

st.set_page_config(page_title="FraudGuard AI - PagoSeguro", page_icon="🛡️", layout="wide")

st.title("🛡️ FraudGuard AI — Monitor de Riesgo Transaccional (PagoSeguro)")
st.markdown("**Arquitectura Híbrida:** Inferencia local en tiempo real (`XGBoost`) + Explicabilidad Regulatoria CMF (`Gemini 2.5 Flash`)")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("Simulador de Pasarela de Pago")
    with st.form("form_tx"):
        id_tx = st.text_input("ID Transacción", value="TX-10025")
        monto = st.number_input("Monto de Compra (USD)", min_value=1.0, max_value=10000.0, value=450.0)
        hora = st.slider("Hora del día (0 - 23 hrs)", 0, 23, 3)
        tx_24h = st.number_input("Transacciones en últimas 24h", min_value=0, max_value=50, value=6)
        distancia = st.number_input("Distancia desde ubicación habitual (km)", min_value=0.0, max_value=5000.0, value=180.0)
        internacional = st.selectbox("¿Comercio Internacional?", options=[0, 1], format_func=lambda x: "Sí (1)" if x == 1 else "No (0)")
        
        enviar = st.form_submit_button("Evaluar Transacción en Vivo")

    if enviar:
        payload = {
            "id_transaccion": id_tx,
            "monto": monto,
            "hora": hora,
            "tx_ultimas_24h": tx_24h,
            "distancia_ubicacion_km": distancia,
            "es_internacional": internacional
        }
        try:
            resp = requests.post(f"{API_URL}/api/v1/evaluar-pago", json=payload, headers=HEADERS)
            if resp.status_code == 200:
                res = resp.json()
                if res["es_fraude"]:
                    st.error(f"{res['estado']} | Riesgo: {res['probabilidad_fraude_pct']}%")
                else:
                    st.success(f"{res['estado']} | Riesgo: {res['probabilidad_fraude_pct']}%")
                
                st.metric("Latencia de Inferencia Modelo (SLA ≤ 100ms)", f"{res['latencia_inferencia_ms']} ms")
                st.info(f"**Justificación Auditoría (AIaaS):** {res['explicacion_auditoria']}")
            else:
                st.warning(f"Error de API: {resp.text}")
        except Exception as e:
            st.error(f"No se pudo conectar con la API FastAPI. Verifica que esté corriendo. ({e})")

with col2:
    st.subheader("Monitoreo Operativo y Auditoría en Vivo")
    try:
        hist_resp = requests.get(f"{API_URL}/api/v1/historial")
        if hist_resp.status_code == 200 and len(hist_resp.json()) > 0:
            data = hist_resp.json()
            df = pd.DataFrame(data)
            
            m1, m2, m3 = st.columns(3)
            total = len(df)
            fraudes = df["es_fraude"].sum()
            lat_prom = df["latencia_inferencia_ms"].mean()
            
            m1.metric("Transacciones Evaluadas", total)
            m2.metric("Fraudes Bloqueados", int(fraudes))
            m3.metric("Latencia Promedio Modelo", f"{lat_prom:.2f} ms")
            
            st.dataframe(df[["id_transaccion", "estado", "probabilidad_fraude_pct", "latencia_inferencia_ms", "explicacion_auditoria"]], use_container_width=True)
        else:
            st.info("Aún no hay transacciones evaluadas en esta sesión. Envía una prueba desde el panel izquierdo.")
    except Exception:
        st.warning("Esperando conexión con el backend FastAPI...")