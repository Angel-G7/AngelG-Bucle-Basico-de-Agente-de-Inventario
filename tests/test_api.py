"""
Tests for the Inventory API.
"""

import csv
import os

import pytest
from fastapi.testclient import TestClient

from api.app import app, PRODUCTS_FILE


@pytest.fixture(autouse=True)
def _clean_csv():
    """Remove products.csv before and after each test for isolation."""
    if os.path.exists(PRODUCTS_FILE):
        os.remove(PRODUCTS_FILE)
    yield
    if os.path.exists(PRODUCTS_FILE):
        os.remove(PRODUCTS_FILE)


client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /inventory
# ---------------------------------------------------------------------------


def test_get_inventory_empty():
    response = client.get("/inventory")
    assert response.status_code == 200
    assert response.json() == []


def test_get_inventory_with_products():
    client.post("/inventory", json={"name": "test1", "quantity": 10, "unit": "unidades"})
    client.post("/inventory", json={"name": "test2", "quantity": 5, "unit": "kg"})
    response = client.get("/inventory")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "test1"
    assert data[1]["name"] == "test2"


# ---------------------------------------------------------------------------
# POST /inventory
# ---------------------------------------------------------------------------


def test_create_product():
    response = client.post("/inventory", json={"name": "leche", "quantity": 30, "unit": "unidades"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "leche"
    assert data["quantity"] == 30.0
    assert data["unit"] == "unidades"
    assert "id" in data


def test_create_product_duplicate_name():
    client.post("/inventory", json={"name": "leche", "quantity": 10, "unit": "unidades"})
    response = client.post("/inventory", json={"name": "leche", "quantity": 20, "unit": "unidades"})
    assert response.status_code == 409
    assert "Ya existe" in response.json()["detail"]


def test_create_product_missing_fields():
    response = client.post("/inventory", json={})
    assert response.status_code == 422


def test_create_product_negative_quantity():
    response = client.post("/inventory", json={"name": "test", "quantity": -1, "unit": "unidades"})
    assert response.status_code == 400
    assert "La cantidad inicial no puede ser negativa" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /inventory/{product_id}
# ---------------------------------------------------------------------------


def test_update_stock_positive_delta():
    resp = client.post("/inventory", json={"name": "test", "quantity": 10, "unit": "unidades"})
    pid = resp.json()["id"]
    response = client.patch(f"/inventory/{pid}", json={"delta": 5})
    assert response.status_code == 200
    assert response.json()["quantity"] == 15.0


def test_update_stock_negative_delta():
    resp = client.post("/inventory", json={"name": "test", "quantity": 10, "unit": "unidades"})
    pid = resp.json()["id"]
    response = client.patch(f"/inventory/{pid}", json={"delta": -3})
    assert response.status_code == 200
    assert response.json()["quantity"] == 7.0


def test_update_stock_insufficient_stock():
    resp = client.post("/inventory", json={"name": "test", "quantity": 2, "unit": "unidades"})
    pid = resp.json()["id"]
    response = client.patch(f"/inventory/{pid}", json={"delta": -5})
    assert response.status_code == 400
    assert "negativo" in response.json()["detail"]


def test_update_stock_product_not_found():
    response = client.patch("/inventory/9999", json={"delta": 5})
    assert response.status_code == 404
    assert "Producto no encontrado" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /inventory/alerts
# ---------------------------------------------------------------------------


def test_alerts_default_threshold():
    client.post("/inventory", json={"name": "bajo", "quantity": 3, "unit": "unidades"})
    client.post("/inventory", json={"name": "alto", "quantity": 20, "unit": "unidades"})
    response = client.get("/inventory/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "bajo"


def test_alerts_custom_threshold():
    client.post("/inventory", json={"name": "item1", "quantity": 5, "unit": "unidades"})
    client.post("/inventory", json={"name": "item2", "quantity": 15, "unit": "unidades"})
    response = client.get("/inventory/alerts?threshold=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "item1"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_csv_persistence():
    client.post("/inventory", json={"name": "persistente", "quantity": 7, "unit": "unidades"})
    assert os.path.exists(PRODUCTS_FILE)

    # Read CSV directly
    with open(PRODUCTS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["name"] == "persistente"
    assert rows[0]["quantity"] == "7.0"


def test_csv_survives_restart():
    client.post("/inventory", json={"name": "test", "quantity": 5, "unit": "kg"})
    # Simulate restart by creating a new TestClient
    client2 = TestClient(app)
    response = client2.get("/inventory")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "test"