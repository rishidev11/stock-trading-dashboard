from fastapi import FastAPI, HTTPException, Query
import yfinance as yf
from typing import Optional
import pandas as pd
from utils import get_conversion_rate, convert_currency, add_technical_features, fetch_news_headlines, analyze_sentiment
from sklearn.ensemble import RandomForestRegressor
import requests

app = FastAPI()


@app.get("/")
def main():
    # Root endpoint returns a welcome message
    return {"message": "Hello, welcome to the Trading Dashboard API"}


@app.get("/api/stock/{symbol}")
def stock_price(symbol: str, target_currency: str = Query("USD")):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Ensure the stock exists and has price data
        if not info or 'currentPrice' not in info:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")


        base_currency = info.get("currency", "USD")
        current = convert_currency(info.get("currentPrice"),base_currency,target_currency)
        previous = convert_currency(info.get("previousClose"),base_currency,target_currency)
        # Return key stock details
        return {
            "symbol": symbol.upper(),
            "current_price": current,
            "previous_close": previous,
            "day_change": round(current - previous, 2),
            "day_change_percent": ((current - previous) / previous) * 100 if previous != 0 else 0,
            "company_name": info.get("longName", "Unknown"),
            "currency": target_currency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data for {symbol}")


@app.get("/api/stock/{symbol}/history")
def stock_history(symbol: str, period: str = Query('3mo'), target_currency: str = Query("USD")):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period=period)
        # Apply rate to all values: row['Open'] * rate, etc.

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

        # Convert historical OHLCV data into JSON-friendly format
        history_data = []
        base_currency = info.get("currency", "USD")
        rate = get_conversion_rate(base_currency, target_currency)

        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row['Open'] * rate, 2),
                "high": round(row['High'] * rate, 2),
                "low": round(row['Low'] * rate, 2),
                "close": round(row['Close'] * rate, 2),
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
def predict_price(symbol: str, windowSize: int = Query(3), target_currency: str = Query("USD")):
    ticker = yf.Ticker(symbol)
    info = ticker.info

    hist = ticker.history(period='3mo')  # Get data directly instead of calling your own API

    if hist.empty:
        raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

    history_data = []
    base_currency = info.get("currency", "USD")
    rate = get_conversion_rate(base_currency, target_currency)

    for date, row in hist.iterrows():
        history_data.append({
            "date": date.strftime("%Y-%m-%d"),
                "open": round(row['Open'] * rate, 2),
                "high": round(row['High'] * rate, 2),
                "low": round(row['Low'] * rate, 2),
                "close": round(row['Close'] * rate, 2),
                "volume": int(row['Volume'])
        })

    # Load data into DataFrame and enrich with technical indicators
    df = pd.DataFrame(history_data)
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

    base_currency = info.get("currency", "USD")

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

