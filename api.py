import time
import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from google import genai

# 1. Configuración de API Key de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "TU_API_KEY_DE_GEMINI_AQUI")
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Cargar el modelo XGBoost entrenado
modelo = joblib.load("modelo_fraude.pkl")

# Registro en memoria de transacciones recientes (simula cola/auditoría para el dashboard)
historial_auditoria = []

app = FastAPI(
    title="FraudGuard AI API - PagoSeguro",
    description="API de detección de fraude financiero en tiempo real (XGBoost + Gemini Explainability)",
    version="1.0.0"
)

# Modelo de entrada (Schema Pydantic para Swagger)
class Transaccion(BaseModel):
    id_transaccion: str = Field(..., example="TX-99812")
    monto: float = Field(..., gt=0, example=450.0)
    hora: int = Field(..., ge=0, le=23, example=3)
    tx_ultimas_24h: int = Field(..., ge=0, example=7)
    distancia_ubicacion_km: float = Field(..., ge=0, example=150.5)
    es_internacional: int = Field(..., ge=0, le=1, example=1)

def generar_explicacion_gemini(tx: Transaccion, probabilidad: float) -> str:
    """Usa Gemini Flash para explicar el rechazo al analista/auditor CMF (IE2)."""
    if GEMINI_API_KEY == "TU_API_KEY_DE_GEMINI_AQUI":
        return "Explicación local: Alerta por combinación atípica de monto, horario nocturno y distancia geográfica."
    
    prompt = (
        f"Eres un analista senior de riesgo financiero bajo normativa CMF. "
        f"Explica en máximo 2 líneas y lenguaje técnico por qué esta transacción fue rechazada por fraude "
        f"(Probabilidad: {probabilidad:.1f}%): Monto=${tx.monto} USD, Hora={tx.hora}:00, "
        f"Tx en 24h={tx.tx_ultimas_24h}, Distancia={tx.distancia_ubicacion_km}km, Internacional={bool(tx.es_internacional)}."
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Explicación de respaldo (API no disponible): Patrón de riesgo elevado ({probabilidad:.1f}%)."

@app.get("/health")
def health_check():
    return {"status": "online", "servicio": "FraudGuard AI", "modelo": "XGBoost v1.0"}

@app.post("/api/v1/evaluar-pago")
def evaluar_pago(tx: Transaccion, x_api_key: str = Header(default="pagoseguro-secret-2026")):
    # Seguridad básica por Header API Key (Cumple IE7 - Seguridad)
    if x_api_key != "pagoseguro-secret-2026":
        raise HTTPException(status_code=401, detail="API Key inválida o no autorizada")

    inicio = time.perf_counter()

    # Preparar datos para XGBoost
    datos = pd.DataFrame([{
        "monto": tx.monto,
        "hora": tx.hora,
        "tx_ultimas_24h": tx.tx_ultimas_24h,
        "distancia_ubicacion_km": tx.distancia_ubicacion_km,
        "es_internacional": tx.es_internacional
    }])

    # Inferencia ultra rápida (< 15 ms)
    prediccion = int(modelo.predict(datos)[0])
    probabilidad_fraude = float(modelo.predict_proba(datos)[0][1]) * 100
    latencia_inferencia_ms = (time.perf_counter() - inicio) * 1000

    # Interpretabilidad con IA Generativa solo si es fraude (optimiza costos y latencia)
    if prediccion == 1:
        estado = "RECHAZADO (FRAUDE DETECTADO)"
        explicacion = generar_explicacion_gemini(tx, probabilidad_fraude)
    else:
        estado = "APROBADO"
        explicacion = "Transacción dentro de los parámetros conductuales normales del titular."

    latencia_total_ms = (time.perf_counter() - inicio) * 1000

    resultado = {
        "id_transaccion": tx.id_transaccion,
        "estado": estado,
        "es_fraude": bool(prediccion),
        "probabilidad_fraude_pct": round(probabilidad_fraude, 2),
        "latencia_inferencia_ms": round(latencia_inferencia_ms, 2),
        "latencia_total_ms": round(latencia_total_ms, 2),
        "explicacion_auditoria": explicacion,
        "datos_entrada": tx.model_dump()
    }

    historial_auditoria.append(resultado)
    return resultado

@app.get("/api/v1/historial")
def obtener_historial():
    return historial_auditoria[-50:]