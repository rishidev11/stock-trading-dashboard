def auth_header(client):
    client.post("/auth/register", json={"email": "p@x.com", "password": "pw"})
    token = client.post("/auth/login", json={"email": "p@x.com", "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_show_empty_portfolio(client):
    headers = auth_header(client)
    response = client.get("/portfolio/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["cash_balance"] == 100000.0
    assert data["holdings"] == []
