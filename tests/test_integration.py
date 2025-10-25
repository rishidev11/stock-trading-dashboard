def test_register_login_and_portfolio_flow(client):
    # Register & login
    client.post("/auth/register", json={"email": "flow@x.com", "password": "pw"})
    token = client.post("/auth/login", json={"email": "flow@x.com", "password": "pw"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Portfolio should start empty
    r = client.get("/portfolio/", headers=headers)
    assert r.status_code == 200
    assert r.json()["holdings"] == []
