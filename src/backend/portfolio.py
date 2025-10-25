from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth import get_current_user
from .database import get_db
from . import models
from pydantic import BaseModel
from fastapi import Query
import requests

router = APIRouter()

# Pydantic model for request validation
class StockQuantity(BaseModel):
    ticker: str
    quantity: float

@router.get("/")
def show_portfolio(db: Session = Depends(get_db), user = Depends(get_current_user)):
    # Fetch all holdings for the authenticated user
    holdings = db.query(models.Holding).filter(models.Holding.user_id == user.id).all()

    portfolio_holdings = []
    total_market_value = 0.0
    total_cost_basis = 0.0

    for holding in holdings:
        # Get current market price for each holding to calculate real-time value
        try:
            resp = requests.get(f"http://localhost:8000/api/stock/{holding.symbol}")
            if resp.status_code == 200:
                current_price = round(resp.json()["current_price"], 2)
            else:
                # Fallback to average purchase price if live data unavailable
                current_price = holding.avg_price
        except:
            current_price = holding.avg_price

        # Calculate P&L metrics
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

    # Calculate portfolio-level metrics
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

    # Validate ticker exists and get current price
    resp = requests.get(f"http://localhost:8000/api/stock/{ticker}")
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Invalid ticker")

    ticker_price = round(resp.json()["current_price"], 2)
    total_price = round(ticker_price * quantity, 2)

    # Check user has sufficient funds
    if user.balance < total_price:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Check if user already holds this stock
    holding = db.query(models.Holding).filter(
        models.Holding.user_id == user.id,
        models.Holding.symbol == ticker
    ).first()

    if holding:
        # Update existing holding: recalculate average price using weighted average
        total_quantity = holding.quantity + quantity
        holding.avg_price = (
            (holding.avg_price * holding.quantity) + (ticker_price * quantity)
        ) / total_quantity
        holding.quantity = total_quantity
    else:
        # Create new holding
        holding = models.Holding(
            user_id=user.id,
            symbol=ticker,
            quantity=quantity,
            avg_price=ticker_price
        )
        db.add(holding)

    # Deduct cost from user balance
    user.balance -= total_price

    # Record transaction for audit trail
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

    # Verify user owns this stock
    holding = db.query(models.Holding).filter(
        models.Holding.user_id == user.id,
        models.Holding.symbol == ticker
    ).first()

    if holding:
        # Prevent short selling - can't sell more than owned
        if quantity > holding.quantity:
            raise HTTPException(status_code=400, detail="Cannot sell more shares than you currently hold")

        # Get current market price
        resp = requests.get(f"http://localhost:8000/api/stock/{ticker}")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Invalid ticker")

        ticker_price = round(resp.json()["current_price"], 2)
        total_price = round(ticker_price * quantity, 2)

        # Credit proceeds to user balance
        user.balance += total_price

        # Remove holding entirely if selling all shares, otherwise reduce quantity
        if quantity == holding.quantity:
            db.delete(holding)
        else:
            holding.quantity -= quantity
            db.add(holding)

        # Record transaction
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


@router.get("/transactions")
def show_transactions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),  # Pagination: default 50, max 100 transactions
    offset: int = 0
):
    # Fetch transaction history with pagination
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user.id)
    total = query.count()
    transactions = (
        query.order_by(models.Transaction.timestamp.desc())  # Most recent first
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