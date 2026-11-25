import random
from locust import HttpUser, task, between

class UsuarioPagoSeguro(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def evaluar_transaccion(self):
        payload = {
            "id_transaccion": f"TX-{random.randint(10000, 99999)}",
            "monto": round(random.uniform(5.0, 1200.0), 2),
            "hora": random.randint(0, 23),
            "tx_ultimas_24h": random.randint(0, 12),
            "distancia_ubicacion_km": round(random.uniform(0.5, 400.0), 1),
            "es_internacional": random.choice([0, 0, 0, 1])
        }
        headers = {"x-api-key": "pagoseguro-secret-2026"}
        self.client.post("/api/v1/evaluar-pago", json=payload, headers=headers)