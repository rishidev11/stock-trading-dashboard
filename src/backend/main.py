from fastapi import FastAPI, HTTPException, Query
import yfinance as yf
from typing import Optional

app = FastAPI()


@app.get("/")
def main():
    return {"message": "Hello, welcome to the Trading Dashboard API"}


@app.get("/api/stock/{symbol}")
def stock_price(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Check if stock exists
        if not info or 'currentPrice' not in info:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        return {
            "symbol": symbol.upper(),
            "current_price": info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "day_change": info.get("currentPrice", 0) - info.get("previousClose", 0),
            "day_change_percent": ((info.get("currentPrice", 0) - info.get("previousClose", 0)) / info.get(
                "previousClose", 1)) * 100,
            "company_name": info.get("longName", "Unknown"),
            "currency": info.get("currency", "USD")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data for {symbol}")


@app.get("/api/stock/{symbol}/history")
def stock_history(symbol: str, period: str = Query('1mo')):
    try:
        ticker = yf.Ticker(symbol)
        # Get actual historical data
        hist = ticker.history(period=period)

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

        # Convert to list of dictionaries for JSON response
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })

        return {
            "symbol": symbol.upper(),
            "period": period,
            "data": history_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history for {symbol}")

@app.get("/api/stock/{symbol}/predict")
def predict_price(symbol: str):
    # Placeholder return
    return {"symbol": symbol.upper(), "predicted_close_price": "Coming Soon"}