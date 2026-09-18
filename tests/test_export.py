import pytest
from app.api.auth import get_current_user
from fastapi.testclient import TestClient
from datetime import date
import io
import csv
import json

@pytest.fixture
def mock_export_auth(app):
    app.dependency_overrides[get_current_user] = lambda: "test_user"
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_export_transactions_csv(client, db_session, mock_export_auth, test_user):
    from app.services.transactions import create_transaction
    await create_transaction(
        db_session,
        user_id="test_user",
        amount=100.0,
        currency="INR",
        is_inflow=True,
        record_date=date.today(),
        vendor_raw="Test Vendor",
        category_id=None,
        auto_categorize=False
    )
    
    response = client.get("/api/v1/export/transactions?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=transactions.csv" in response.headers["content-disposition"]
    
    csv_content = response.text
    assert "id,amount,currency,is_inflow,record_date,vendor_raw,category_id,status" in csv_content
    assert "Test Vendor" in csv_content
    assert "100.0,INR,True" in csv_content or "100.0,INR,True" in csv_content.replace(' ','')

@pytest.mark.asyncio
async def test_export_transactions_json(client, db_session, mock_export_auth, test_user):
    from app.services.transactions import create_transaction
    tx = await create_transaction(
        db_session,
        user_id="test_user",
        amount=99.0,
        currency="INR",
        is_inflow=False,
        record_date=date.today(),
        vendor_raw="JSON Vendor",
        category_id=None,
        auto_categorize=False
    )
    
    response = client.get("/api/v1/export/transactions?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert isinstance(data, list)
    assert any(item.get("vendor_raw") == "JSON Vendor" for item in data)

@pytest.mark.asyncio
async def test_export_budget_csv(client, db_session, mock_export_auth, test_user):
    response = client.get("/api/v1/export/budget?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    csv_content = response.text
    assert "total_income,total_expense,net_balance,currency" in csv_content
    assert "category,amount,budget,utilization" in csv_content

@pytest.mark.asyncio
async def test_export_budget_json(client, db_session, mock_export_auth, test_user):
    response = client.get("/api/v1/export/budget?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert "total_income" in data
    assert "total_expense" in data
    assert "breakdown" in data