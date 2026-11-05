"""Tests for the restocking endpoints."""
import pytest

import main


@pytest.fixture(autouse=True)
def clear_orders():
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


def test_zero_budget_recommends_nothing_but_reports_max(client):
    data = client.get("/api/restocking/recommendations?budget=0").json()
    assert data["items"] == []
    assert data["max_budget"] > 0
    assert data["lead_time_days"] == 14


def test_full_budget_recommends_all_shortfall_items_only(client):
    max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
    data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
    skus = {i["sku"] for i in data["items"]}
    assert "MTR-304" not in skus  # decreasing trend, stock covers demand
    assert "BRG-102" not in skus  # stock covers demand
    assert "FLT-405" in skus
    assert data["remaining"] == pytest.approx(0, abs=0.01)


def test_recommendations_never_exceed_budget_and_prefer_best_value(client):
    data = client.get("/api/restocking/recommendations?budget=5000").json()
    assert data["total_cost"] <= 5000
    costs = [i["unit_cost"] for i in data["items"]]
    assert costs == sorted(costs)  # cheapest unit cost = most units per dollar first


def test_negative_budget_rejected(client):
    assert client.get("/api/restocking/recommendations?budget=-1").status_code == 400


def test_place_order_and_list(client):
    payload = {"budget": 10000, "items": [{"sku": "FLT-405", "quantity": 100}]}
    response = client.post("/api/restocking/orders", json=payload)
    assert response.status_code == 201
    order = response.json()
    assert order["order_number"].startswith("RST-")
    assert order["lead_time_days"] == 14
    assert order["total_value"] == pytest.approx(940.0)

    listed = client.get("/api/restocking/orders").json()
    assert [o["id"] for o in listed] == [order["id"]]


def test_order_over_budget_rejected(client):
    payload = {"budget": 100, "items": [{"sku": "FLT-405", "quantity": 100}]}
    assert client.post("/api/restocking/orders", json=payload).status_code == 400


def test_order_unknown_sku_and_empty_rejected(client):
    assert client.post("/api/restocking/orders",
                       json={"budget": 1000, "items": [{"sku": "NOPE", "quantity": 1}]}).status_code == 400
    assert client.post("/api/restocking/orders", json={"budget": 1000, "items": []}).status_code == 400
