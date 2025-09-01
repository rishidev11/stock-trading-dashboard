from fastapi import FastAPI, HTTPException, Query
import yfinance as yf
from typing import Optional
import pandas as pd
from utils import slidingWindow, add_technical_features
from sklearn.ensemble import RandomForestRegressor

import requests

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
def stock_history(symbol: str, period: str = Query('3mo')):
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
def predict_price(symbol: str, windowSize: int = Query(3)):
    response = requests.get(f"http://localhost:8000/api/stock/{symbol}/history")
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Failed to retrieve historical data")

    df = pd.DataFrame(response.json()["data"])
    df = add_technical_features(df)
    df = df.dropna().reset_index(drop=True)

    feature_cols = ["close", "SMA_5", "SMA_20", "RSI", "volume_ratio"]
    x_values = []
    y_values = []

    for i in range(len(df) - windowSize):
        window = df.iloc[i:i + windowSize][feature_cols].values.flatten()
        target = df.iloc[i + windowSize]["close"]
        x_values.append(window)
        y_values.append(target)


    if len(x_values) == 0 or len(y_values) == 0:
        raise HTTPException(status_code=400, detail="Not enough data for the given window size.")

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(x_values, y_values)

    lastWindow = df.iloc[-windowSize:][feature_cols].values.flatten()
    prediction = model.predict([lastWindow])
    df[feature_cols] = df[feature_cols].round(2)

    print("Predicted next close:", prediction[0])
    return {
        "symbol": symbol.upper(),
        "last_window": df.iloc[-windowSize:][feature_cols].to_dict(orient="records"),
        "predicted_close_price": round(prediction[0], 2)
    }














