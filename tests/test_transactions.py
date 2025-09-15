# tests/test_transactions.py
def auth_header(client):
    client.post("/auth/register", json={"email": "t@x.com", "password": "pw"})
    token = client.post("/auth/login", json={"email": "t@x.com", "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_transactions_empty(client):
    headers = auth_header(client)
    response = client.get("/portfolio/transactions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["transactions"] == []
