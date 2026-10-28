"""Pruebas de la API REST con TestClient (httpx)."""
import pytest
from fastapi.testclient import TestClient

from app import api


@pytest.fixture
def client():
    api.repository.reset()          # fixtures frescos en cada prueba
    return TestClient(api.app)


def test_get_order(client):
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert (body["status"], body["units"], body["total"]) == ("DRAFT", 4, "2100.00")


def test_lista_16_pedidos(client):
    assert len(client.get("/orders").json()) == 16


def test_404_pedido_inexistente(client):
    assert client.get("/orders/O999").status_code == 404
    r = client.post("/orders/O999/confirm")
    assert r.status_code == 404 and "No existe" in r.json()["detail"]


def test_confirmar_exitoso_200(client):
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json() == {"id": "O013", "status": "CONFIRMED", "events": ["OrderConfirmed"]}


def test_409_confirmacion_doble(client):
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 409
    assert client.get("/orders/O013").json()["events"].__len__() == 1


def test_422_confirmar_sin_articulos(client):
    r = client.post("/orders/O007/confirm")
    assert r.status_code == 422
    assert client.get("/orders/O007").json()["status"] == "DRAFT"


def test_422_cliente_inactivo(client):
    assert client.post("/orders/O003/confirm").status_code == 422


def test_422_envio_sin_guia(client):
    client.post("/orders/O012/confirm")
    assert client.post("/orders/O012/ship", json={}).status_code == 422
    assert client.post("/orders/O012/ship").status_code == 422
    assert client.get("/orders/O012").json()["status"] == "CONFIRMED"


def test_409_cancelar_desde_shipped(client):
    client.post("/orders/O014/confirm")
    assert client.post("/orders/O014/ship",
                       json={"tracking_number": "GUIA-MX-0001"}).status_code == 200
    r = client.post("/orders/O014/cancel", json={"reason": "motivo"})
    assert r.status_code == 409
    assert client.get("/orders/O014").json()["status"] == "SHIPPED"


def test_cancelar_desde_confirmed(client):
    client.post("/orders/O014/confirm")
    assert client.post("/orders/O014/cancel", json={"reason": ""}).status_code == 422
    r = client.post("/orders/O014/cancel", json={"reason": "Cliente lo pidió"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_flujo_entrega_y_devolucion(client):
    for oid, op, final in [("O016", "deliver", "DELIVERED"), ("O015", "return", "RETURNED")]:
        client.post(f"/orders/{oid}/confirm")
        client.post(f"/orders/{oid}/ship", json={"tracking_number": "G1"})
        r = client.post(f"/orders/{oid}/{op}")
        assert r.status_code == 200 and r.json()["status"] == final


def test_422_limite_21_unidades(client):
    r = client.post("/orders/O009/items", json={"sku": "SKU003", "quantity": 2})
    assert r.status_code == 422
    assert client.get("/orders/O009").json()["units"] == 19


def test_crear_pedido_y_agregar_articulo(client):
    r = client.post("/orders", json={"customer_id": "C002"})
    assert r.status_code == 201 and r.json()["id"] == "O017"
    r = client.post("/orders/O017/items", json={"sku": "SKU001", "quantity": 2})
    assert r.status_code == 200 and r.json()["total"] == "1200.00"
    assert client.post("/orders", json={"customer_id": "C999"}).status_code == 404
    assert client.post("/orders/O017/items",
                       json={"sku": "SKU999", "quantity": 1}).status_code == 404


def test_descuento_endpoint(client):
    assert client.get("/orders/O001/discount").json()["percent"] == "10%"
    assert client.get("/orders/O006/discount").json()["percent"] == "5%"
    assert client.get("/orders/O005/discount").json()["percent"] == "0%"


def test_reset_recarga_fixtures(client):
    client.post("/orders/O013/confirm")
    assert client.post("/reset").json()["orders"] == 16
    assert client.get("/orders/O013").json()["status"] == "DRAFT"


def test_openapi_y_docs(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/orders/{order_id}", "/orders/{order_id}/confirm",
              "/orders/{order_id}/ship", "/orders/{order_id}/cancel"]:
        assert p in paths
    assert "post" in paths["/orders/{order_id}/confirm"]
