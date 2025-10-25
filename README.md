# Stock Trading Dashboard

A web-based stock trading platform with real-time data, machine learning price predictions, and portfolio management.

## Features

- **Live Stock Data** - Real-time prices and historical charts with multi-currency support
- **ML Price Prediction** - Random Forest model forecasts next-day closing prices using technical indicators
- **Sentiment Analysis** - News-based sentiment scoring for stocks
- **Portfolio Management** - Buy/sell stocks, track P&L, and view transaction history
- **User Authentication** - Secure login and registration system

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, scikit-learn
- **Frontend**: Streamlit
- **Data Source**: yfinance API

## Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

## Running the Application

Open **two terminals**:

**Terminal 1 - Backend:**
```bash
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
streamlit run frontend/app.py
```

Then open your browser:
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/

## API Endpoints

- `GET /api/stock/{symbol}` - Current stock price
- `GET /api/stock/{symbol}/history` - Historical data
- `GET /api/stock/{symbol}/predict` - ML price prediction
- `GET /api/stock/{symbol}/sentiment` - News sentiment
- `POST /portfolio/buy` - Buy stocks
- `POST /portfolio/sell` - Sell stocks

## Notes

This is an educational project demonstrating full-stack development with ML integration. Uses delayed market data (not for real trading).
