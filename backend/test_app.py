"""
Basic smoke tests for the CBE District IT Management API.
Run with: pytest test_app.py
"""
import pytest
from app import create_app
from models import db, User, Branch


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    with app.app_context():
        db.create_all()
        admin = User(full_name="Test Admin", username="testadmin", email="a@a.com", role="district_admin")
        admin.set_password("Password123")
        db.session.add(admin)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def auth_headers(client):
    resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "Password123"})
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "Password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_failure(client):
    resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "wrong"})
    assert resp.status_code == 401


def test_requires_auth(client):
    resp = client.get("/api/branches")
    assert resp.status_code == 401


def test_create_and_list_branch(client):
    headers = auth_headers(client)
    resp = client.post("/api/branches", json={"branch_code": "T001", "name": "Test Branch"}, headers=headers)
    assert resp.status_code == 201
    resp = client.get("/api/branches", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_create_atm_and_simulated_check(client):
    headers = auth_headers(client)
    b = client.post("/api/branches", json={"branch_code": "T002", "name": "ATM Branch"}, headers=headers).get_json()
    resp = client.post("/api/atms", json={"atm_code": "ATM-999", "branch_id": b["id"]}, headers=headers)
    assert resp.status_code == 201
    atm_id = resp.get_json()["id"]
    check_resp = client.post(f"/api/atms/{atm_id}/check", json={}, headers=headers)
    assert check_resp.status_code == 200
    body = check_resp.get_json()
    assert body["check"]["is_simulated"] is True


def test_ticket_creation(client):
    headers = auth_headers(client)
    b = client.post("/api/branches", json={"branch_code": "T003", "name": "Ticket Branch"}, headers=headers).get_json()
    resp = client.post(
        "/api/tickets",
        json={"branch_id": b["id"], "problem_category": "Slow computer", "description": "Test"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "OPEN"


def test_role_restriction(client):
    headers = auth_headers(client)
    # create a technician user and login as them
    client.post(
        "/api/users",
        json={
            "full_name": "Tech One", "username": "techone", "email": "t1@a.com",
            "password": "Tech@1234", "role": "technician",
        },
        headers=headers,
    )
    login = client.post("/api/auth/login", json={"username": "techone", "password": "Tech@1234"})
    tech_headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
    # technicians cannot create branches
    resp = client.post("/api/branches", json={"branch_code": "X1", "name": "X"}, headers=tech_headers)
    assert resp.status_code == 403
