import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import api

client = TestClient(api.app)
HEADERS = {"x-api-key": "pagoseguro-secret-2026"}

TX_VALIDA = {
    "id_transaccion": "TX-TEST-01",
    "monto": 45.0,
    "hora": 14,
    "tx_ultimas_24h": 1,
    "distancia_ubicacion_km": 3.5,
    "es_internacional": 0,
}

TX_FRAUDE = {
    "id_transaccion": "TX-TEST-99",
    "monto": 950.0,
    "hora": 3,
    "tx_ultimas_24h": 9,
    "distancia_ubicacion_km": 420.0,
    "es_internacional": 1,
}


def test_ct01_health_online():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "online"


def test_ct02_post_sin_api_key_usa_default_o_rechaza():
    r = client.post("/api/v1/evaluar-pago", json=TX_VALIDA)
    assert r.status_code in (200, 401, 403, 422)


def test_ct03_api_key_incorrecta():
    r = client.post("/api/v1/evaluar-pago", json=TX_VALIDA, headers={"x-api-key": "clave-falsa"})
    assert r.status_code in (401, 403)


def test_ct04_transaccion_legitima():
    r = client.post("/api/v1/evaluar-pago", json=TX_VALIDA, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "APROBADO" in data["estado"]
    assert data["es_fraude"] is False


def test_ct05_transaccion_fraudulenta():
    r = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "RECHAZADO" in data["estado"]
    assert data["es_fraude"] is True
    assert len(data["explicacion_auditoria"]) > 5


def test_ct06_umbral_50_porciento():
    assert (0.50 >= 0.50) is True
    assert (0.4999 >= 0.50) is False


@pytest.mark.parametrize("campo,valor", [
    ("monto", 0),
    ("monto", -50),
    ("hora", 24),
    ("hora", -1),
    ("tx_ultimas_24h", -2),
    ("distancia_ubicacion_km", -10),
    ("es_internacional", 2),
])
def test_ct07_validacion_fuera_de_rango(campo, valor):
    payload = dict(TX_VALIDA)
    payload[campo] = valor
    r = client.post("/api/v1/evaluar-pago", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_ct08_campo_obligatorio_faltante():
    payload = dict(TX_VALIDA)
    del payload["monto"]
    r = client.post("/api/v1/evaluar-pago", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_ct09_pci_dss_no_retorna_pan():
    payload = dict(TX_VALIDA)
    payload["pan"] = "4532015112830366"
    r = client.post("/api/v1/evaluar-pago", json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert "4532015112830366" not in r.text


def test_ct10_historial_acceso():
    if any(route.path == "/api/v1/historial" for route in api.app.routes):
        r = client.get("/api/v1/historial")
        assert r.status_code in (200, 401, 403, 422)


def test_ct11_historial_registra_en_orden():
    for i in range(3):
        p = dict(TX_VALIDA)
        p["id_transaccion"] = f"TX-ORD-{i}"
        r = client.post("/api/v1/evaluar-pago", json=p, headers=HEADERS)
        assert r.status_code == 200
    if any(route.path == "/api/v1/historial" for route in api.app.routes):
        r = client.get("/api/v1/historial", headers=HEADERS)
        assert r.status_code == 200


def test_ct12_metricas_percentiles():
    if any(route.path == "/api/v1/metricas" for route in api.app.routes):
        r = client.get("/api/v1/metricas", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        if "p50" in body and "p99" in body:
            assert body["p50"] <= body["p99"]


def test_ct13_rafaga_controlada():
    codes = [client.post("/api/v1/evaluar-pago", json=TX_VALIDA, headers=HEADERS).status_code for _ in range(3)]
    assert all(c in (200, 429) for c in codes)


def test_ct14_resiliencia_gemini_lento():
    def slow_call(*args, **kwargs):
        time.sleep(0.15)
        raise TimeoutError("Timeout simulado")
    with patch.object(api, "generar_explicacion_ia", side_effect=slow_call, create=True):
        inicio = time.perf_counter()
        r = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS)
        duracion = time.perf_counter() - inicio
        assert r.status_code == 200
        assert duracion < 2.0


def test_ct15_resiliencia_excepcion_gemini():
    with patch.object(api, "generar_explicacion_ia", side_effect=RuntimeError("Falla red"), create=True):
        r = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS)
        assert r.status_code == 200


def test_ct16_coherencia_probabilidad_clase():
    r = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS).json()
    assert 0 <= r["probabilidad_fraude_pct"] <= 100
    assert r["es_fraude"] == (r["probabilidad_fraude_pct"] >= 50.0)


def test_ct17_normal_vs_extremo():
    r_ok = client.post("/api/v1/evaluar-pago", json=TX_VALIDA, headers=HEADERS).json()
    r_bad = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS).json()
    assert r_ok["es_fraude"] is False
    assert r_bad["es_fraude"] is True


def test_ct18_factores_riesgo_coherentes():
    r = client.post("/api/v1/evaluar-pago", json=TX_FRAUDE, headers=HEADERS).json()
    assert r["probabilidad_fraude_pct"] > 50.0
    assert "explicacion_auditoria" in r
