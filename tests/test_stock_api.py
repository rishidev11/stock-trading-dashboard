def test_stock_price_invalid_symbol(client, monkeypatch):
    def mock_ticker(symbol):
        class MockTicker:
            info = {}
        return MockTicker()
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", mock_ticker)

    response = client.get("/api/stock/FAKE")
    assert response.status_code == 404
