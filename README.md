# 🛡️ FraudGuard AI — Motor de Detección de Fraude en Tiempo Real (PagoSeguro)

Sistema de detección preventiva de fraude financiero en tiempo real diseñado bajo una **arquitectura híbrida de baja latencia**, cumpliendo con los estándares de disponibilidad, seguridad (**PCI-DSS**) y explicabilidad regulatoria (**CMF - Comisión para el Mercado Financiero**).

---

## 🏗️ Arquitectura del Sistema

El sistema desacopla la inferencia crítica de baja latencia de la generación de explicaciones para auditoría:

```text
+-------------------+       HTTP/JSON (API Key)       +-----------------------------------+
|  Pasarela / UI    | ------------------------------> |        FastAPI Backend (8000)     |
| (Streamlit 8501)  |                                 |  1. Validación Pydantic & Auth    |
+-------------------+ <------------------------------ |  2. Inferencia XGBoost (< 15 ms)  |
                             Respuesta + Auditoría    |  3. Explicabilidad Gemini 2.5     |
                                                      +-----------------------------------+
```

* **Motor de Inferencia (`XGBoost`):** Evalúa patrones transaccionales (monto, horario, frecuencia en 24h, distancia geográfica y origen internacional) en **< 15 ms**, garantizando el SLA estricto de `< 100 ms` por operación.
* **Explicabilidad Regulatoria (`Google Gemini 2.5 Flash`):** Se activa únicamente cuando se detecta una transacción fraudulenta para generar una justificación técnica auditable sin penalizar la latencia de los pagos legítimos.
* **API REST (`FastAPI`):** Expone endpoints documentados bajo estándar OpenAPI/Swagger con validación de esquemas y autenticación mediante cabecera `x-api-key`.
* **Monitor Operativo (`Streamlit`):** Interfaz interactiva para simulación de transacciones en vivo y visualización del historial de auditoría.

---

## 📂 Estructura del Repositorio

```text
├── api.py                  # Microservicio REST en FastAPI (XGBoost + Gemini API)
├── dashboard.py            # Interfaz web operativa en Streamlit
├── train.py                # Pipeline de generación de dataset sintético y entrenamiento XGBoost
├── modelo_fraude.pkl       # Modelo XGBoost serializado listo para producción
├── locustfile.py           # Suite de pruebas de carga y estrés distribuido
├── Dockerfile              # Imagen base optimizada (Python 3.11-slim)
├── docker-compose.yml      # Orquestación multi-contenedor (API + Dashboard)
├── requirements.txt        # Dependencias del proyecto
└── README.md               # Documentación técnica
```

---

## 🚀 Despliegue Rápido con Docker (Recomendado)

### 1. Prerrequisitos
* Docker y Docker Compose v2 instalados.
* Una API Key válida de **Google AI Studio (Gemini)**.

### 2. Configuración de Variables de Entorno
Por seguridad (cumplimiento PCI-DSS / OWASP), las credenciales nunca se almacenan en el código fuente. Crea un archivo `.env` en la raíz del proyecto antes de levantar los contenedores:

```bash
echo "GEMINI_API_KEY=tu_clave_secreta_de_gemini_aqui" > .env
```

### 3. Construcción y Ejecución
Ejecuta el siguiente comando para compilar las imágenes y levantar ambos servicios en segundo plano:

```bash
sudo docker compose up -d --build
```

Verifica que ambos contenedores estén activos:

```bash
sudo docker ps
```

### 4. Acceso a los Servicios
* **Dashboard Operativo (Streamlit):** `http://<IP_SERVIDOR>:8501`
* **Documentación Interactiva API (Swagger UI):** `http://<IP_SERVIDOR>:8000/docs`
* **Health Check:** `http://<IP_SERVIDOR>:8000/health`

---

## 💻 Ejecución en Entorno Local (Desarrollo)

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. *(Opcional)* Reentrenar el modelo predictivo:
   ```bash
   python train.py
   ```
3. Iniciar el backend FastAPI:
   ```bash
   uvicorn api:app --reload --port 8000
   ```
4. En una segunda terminal, iniciar el dashboard:
   ```bash
   streamlit run dashboard.py
   ```

---

## 🔌 Ejemplo de Uso de la API

**Endpoint:** `POST /api/v1/evaluar-pago`  
**Header requerido:** `x-api-key: pagoseguro-secret-2026`

```bash
curl -X POST "http://localhost:8000/api/v1/evaluar-pago" \
     -H "Content-Type: application/json" \
     -H "x-api-key: pagoseguro-secret-2026" \
     -d '{
           "id_transaccion": "TX-99812",
           "monto": 850.0,
           "hora": 3,
           "tx_ultimas_24h": 8,
           "distancia_ubicacion_km": 320.5,
           "es_internacional": 1
         }'
```

---

## 📊 Pruebas de Carga y Rendimiento (Locust)

Para validar el cumplimiento del SLA (`< 100 ms` de latencia y `0%` de tasa de error bajo concurrencia), ejecuta la suite de pruebas de estrés:

```bash
locust -f locustfile.py --host=http://localhost:8000
```
Accede a `http://localhost:8089` para configurar la simulación de usuarios concurrentes.

---

## 🔒 Seguridad y Cumplimiento Normativo
* **Gestión de Secretos:** Inyección de claves vía variables de entorno (`.env` excluido mediante `.gitignore`).
* **Control de Acceso:** Autenticación mediante `API Key` en cabeceras HTTP.
* **Privacidad de Datos (PCI-DSS):** El motor de inferencia procesa únicamente metadatos conductuales anonimizados; no recibe ni almacena números de tarjeta (PAN) ni códigos CVV.