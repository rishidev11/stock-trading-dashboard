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

    portfolio_holdings = []
    total_market_value = 0.0
    total_cost_basis = 0.0

    for holding in holdings:
        # Get current price for each holding
        try:
            resp = requests.get(f"http://localhost:8000/api/stock/{holding.symbol}")
            if resp.status_code == 200:
                current_price = round(resp.json()["current_price"], 2)
            else:
                # Fallback to avg price if API fails
                current_price = holding.avg_price
        except:
            # Fallback on error
            current_price = holding.avg_price

        market_value = round(current_price * holding.quantity, 2)
        cost_basis = round(holding.avg_price * holding.quantity, 2)
        unrealised_pnl = round(market_value - cost_basis, 2)

        total_market_value += market_value
        total_cost_basis += cost_basis

        portfolio_holdings.append({
            "symbol": holding.symbol,
            "quantity": holding.quantity,
            "avg_price": holding.avg_price,
            "current_price": current_price,
            "market_value": market_value,
            "cost_basis": cost_basis,
            "unrealised_pnl": unrealised_pnl,
            "pnl_percentage": round((unrealised_pnl / cost_basis * 100), 2) if cost_basis > 0 else 0
        })

    total_unrealised_pnl = round(total_market_value - total_cost_basis, 2)
    total_portfolio_value = round(user.balance + total_market_value, 2)

    return {
        "user": user.email,
        "cash_balance": round(user.balance, 2),
        "holdings_market_value": round(total_market_value, 2),
        "total_portfolio_value": total_portfolio_value,
        "total_unrealised_pnl": total_unrealised_pnl,
        "pnl_percentage": round((total_unrealised_pnl / total_cost_basis * 100), 2) if total_cost_basis > 0 else 0,
        "holdings": portfolio_holdings
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



@router.post("/sell")
def sell_stock(shares: StockQuantity, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticker = shares.ticker.upper()
    quantity = shares.quantity

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    holding = db.query(models.Holding).filter(
        models.Holding.user_id == user.id,
        models.Holding.symbol == ticker
    ).first()

    if holding:
        if quantity > holding.quantity:
            raise HTTPException(status_code=400, detail="Cannot sell more shares than you currently hold")

        resp = requests.get(f"http://localhost:8000/api/stock/{ticker}")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Invalid ticker")

        ticker_price = round(resp.json()["current_price"], 2)
        total_price = round(ticker_price * quantity, 2)

        user.balance += total_price

        if quantity == holding.quantity:
            db.delete(holding)
        else:
            holding.quantity -= quantity
            db.add(holding)

        transaction = models.Transaction(
            user_id=user.id,
            symbol=ticker,
            trade_type="SELL",
            quantity=quantity,
            price=ticker_price,
            amount=total_price,
            timestamp=datetime.utcnow()
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return {
            "message": f"Sold {quantity} shares of {ticker} at {ticker_price:.2f}",
            "user": user.email,
            "balance": user.balance,
            "timestamp": transaction.timestamp.isoformat()
        }

    else:
        raise HTTPException(status_code=400, detail="No holding of this stock exists")


from fastapi import Query

@router.get("/transactions")
def show_transactions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = 0
):
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user.id)
    total = query.count()
    transactions = (
        query.order_by(models.Transaction.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "transactions": [
            {
                "symbol": t.symbol,
                "trade_type": t.trade_type,
                "quantity": t.quantity,
                "price": t.price,
                "amount": t.amount,
                "timestamp": t.timestamp.isoformat()
            } for t in transactions
        ]
    }
