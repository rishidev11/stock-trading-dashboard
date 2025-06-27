from fastapi import FastAPI
import yfinance as yf

app = FastAPI()

@app.get("/")
def main():
    return "Hello, welcome to the Dashboard"

@app.get("/api/stock/{symbol}")
def stock_price(symbol: str):
    dat = yf.Ticker(symbol)
    price = dat.info.get("currentPrice")
    return f"{symbol} Price: {price}"

@app.get("/api/stock/{symbol}/history")
def stock_history(symbol: str):
    dat = yf.Ticker(symbol)
    return (f"symbol: {symbol}, "
            f"history: {dat.get_history_metadata()}")

