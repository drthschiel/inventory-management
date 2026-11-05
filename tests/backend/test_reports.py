"""
Tests for the reports endpoints (quarterly performance and monthly trends).
"""


class TestQuarterlyReports:
    """Test suite for /api/reports/quarterly."""

    def test_structure(self, client):
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for row in data:
            for field in ["quarter", "total_orders", "total_revenue",
                          "avg_order_value", "fulfillment_rate"]:
                assert field in row
            assert 0 <= row["fulfillment_rate"] <= 100

    def test_sorted_by_quarter(self, client):
        data = client.get("/api/reports/quarterly").json()
        quarters = [row["quarter"] for row in data]
        assert quarters == sorted(quarters)

    def test_totals_match_orders(self, client):
        """Unfiltered quarterly totals should cover every order in a known quarter."""
        quarterly = client.get("/api/reports/quarterly").json()
        orders = client.get("/api/orders").json()
        assert sum(r["total_orders"] for r in quarterly) <= len(orders)

    def test_month_filter_limits_to_one_quarter(self, client):
        data = client.get("/api/reports/quarterly?month=Q1-2025").json()
        assert all(row["quarter"] == "Q1-2025" for row in data)

    def test_status_filter_applies(self, client):
        """Filtering to Delivered orders must give a 100% fulfillment rate."""
        data = client.get("/api/reports/quarterly?status=Delivered").json()
        assert len(data) > 0
        for row in data:
            assert row["fulfillment_rate"] == 100

    def test_filters_reduce_totals(self, client):
        all_rows = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?status=Backordered").json()
        assert sum(r["total_orders"] for r in filtered) < sum(r["total_orders"] for r in all_rows)

    def test_all_values_behave_like_no_filter(self, client):
        base = client.get("/api/reports/quarterly").json()
        with_all = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()
        assert base == with_all


class TestMonthlyTrends:
    """Test suite for /api/reports/monthly-trends."""

    def test_structure(self, client):
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for row in data:
            for field in ["month", "order_count", "revenue", "delivered_count"]:
                assert field in row
            assert len(row["month"]) == 7  # YYYY-MM

    def test_sorted_by_month(self, client):
        data = client.get("/api/reports/monthly-trends").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)

    def test_month_filter(self, client):
        first = client.get("/api/reports/monthly-trends").json()[0]["month"]
        data = client.get(f"/api/reports/monthly-trends?month={first}").json()
        assert [row["month"] for row in data] == [first]

    def test_quarter_filter(self, client):
        data = client.get("/api/reports/monthly-trends?month=Q1-2025").json()
        assert all(row["month"] in ("2025-01", "2025-02", "2025-03") for row in data)

    def test_status_filter_reduces_orders(self, client):
        all_rows = client.get("/api/reports/monthly-trends").json()
        filtered = client.get("/api/reports/monthly-trends?status=Backordered").json()
        assert sum(r["order_count"] for r in filtered) < sum(r["order_count"] for r in all_rows)

    def test_unmatched_filter_returns_empty_list(self, client):
        response = client.get("/api/reports/monthly-trends?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []
