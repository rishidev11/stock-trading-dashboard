from fastapi import FastAPI, HTTPException, Query
import yfinance as yf
from typing import Optional
import pandas as pd
from utils import add_technical_features, fetch_news_headlines, analyze_sentiment
from sklearn.ensemble import RandomForestRegressor
import requests

app = FastAPI()


@app.get("/")
def main():
    # Root endpoint returns a welcome message
    return {"message": "Hello, welcome to the Trading Dashboard API"}


@app.get("/api/stock/{symbol}")
def stock_price(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Ensure the stock exists and has price data
        if not info or 'currentPrice' not in info:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        # Return key stock details
        return {
            "symbol": symbol.upper(),
            "current_price": info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "day_change": info.get("currentPrice", 0) - info.get("previousClose", 0),
            "day_change_percent": ((info.get("currentPrice", 0) - info.get("previousClose", 0)) / info.get("previousClose", 1)) * 100,
            "company_name": info.get("longName", "Unknown"),
            "currency": info.get("currency", "USD")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data for {symbol}")


@app.get("/api/stock/{symbol}/history")
def stock_history(symbol: str, period: str = Query('3mo')):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

        # Convert historical OHLCV data into JSON-friendly format
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
    # Get historical data from our own API
    response = requests.get(f"http://localhost:8000/api/stock/{symbol}/history")
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Failed to retrieve historical data")

    # Load data into DataFrame and enrich with technical indicators
    df = pd.DataFrame(response.json()["data"])
    df = add_technical_features(df)
    df = df.dropna().reset_index(drop=True)  # Drop rows with NaNs caused by rolling indicators

    # Select feature columns to train the model on
    feature_cols = ["close", "SMA_5", "SMA_20", "RSI", "volume_ratio"]
    x_values = []
    y_values = []

    # Construct input/output pairs using sliding window on technical features
    for i in range(len(df) - windowSize):
        window = df.iloc[i:i + windowSize][feature_cols].values.flatten()
        target = df.iloc[i + windowSize]["close"]
        x_values.append(window)
        y_values.append(target)

    if len(x_values) == 0 or len(y_values) == 0:
        raise HTTPException(status_code=400, detail="Not enough data for the given window size.")

    # Train model using historical feature windows
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(x_values, y_values)

    # Predict next close based on most recent feature window
    lastWindow = df.iloc[-windowSize:][feature_cols].values.flatten()
    prediction = model.predict([lastWindow])
    df[feature_cols] = df[feature_cols].round(2)

    return {
        "symbol": symbol.upper(),
        "last_window": df.iloc[-windowSize:][feature_cols].to_dict(orient="records"),
        "predicted_close_price": round(prediction[0], 2)
    }

@app.get("/api/stock/{symbol}/sentiment")
def get_sentiment(symbol: str):
    headlines = fetch_news_headlines(symbol)
    score = analyze_sentiment(headlines)
    return {
        "symbol": symbol.upper(),
        "sentiment_score": round(score, 3),
        "status": (
            "Positive" if score > 0.05 else
            "Negative" if score < -0.05 else
            "Neutral"
        ),
        "headlines": headlines
    }

