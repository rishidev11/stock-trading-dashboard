from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth import get_db, get_current_user
from . import models
from pydantic import BaseModel
import requests

router = APIRouter()

class StockQuantity(BaseModel):
    ticker: str
    quantity: float

@router.get("/")
def show_portfolio(db: Session = Depends(get_db), user = Depends(get_current_user)):
    holdings = db.query(models.Holding).filter(models.Holding.user_id == user.id).all()
    return {
        "user": user.email,
        "balance": user.balance,
        "holdings": [{"stock": h.symbol, "quantity": h.quantity} for h in holdings]
    }

@router.post("/buy")
def buy_stock(shares: StockQuantity, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticker = shares.ticker.upper()
    quantity = shares.quantity

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    resp = requests.get(f"http://localhost:8000/api/stock/{ticker}")
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Invalid ticker")

    ticker_price = round(resp.json()["current_price"], 2)
    total_price = round(ticker_price * quantity, 2)

    if user.balance < total_price:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    holding = db.query(models.Holding).filter(
        models.Holding.user_id == user.id,
        models.Holding.symbol == ticker
    ).first()

    if holding:
        total_quantity = holding.quantity + quantity
        holding.avg_price = (
            (holding.avg_price * holding.quantity) + (ticker_price * quantity)
        ) / total_quantity
        holding.quantity = total_quantity
    else:
        holding = models.Holding(
            user_id=user.id,
            symbol=ticker,
            quantity=quantity,
            avg_price=ticker_price
        )
        db.add(holding)

    user.balance -= total_price

    transaction = models.Transaction(
        user_id=user.id,
        symbol=ticker,
        trade_type="BUY",
        quantity=quantity,
        price=ticker_price,
        amount=total_price,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)

    db.commit()
    db.refresh(holding)
    db.refresh(transaction)

    return {
        "message": f"Bought {quantity} shares of {ticker} at {ticker_price:.2f}",
        "user": user.email,
        "balance": round(user.balance, 2),
        "timestamp": transaction.timestamp.isoformat()
    }











