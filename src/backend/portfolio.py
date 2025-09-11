from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .auth import get_db, get_current_user
from . import models

router = APIRouter()

@router.get("/")
def show_portfolio(db: Session = Depends(get_db), user = Depends(get_current_user)):
    holdings = db.query(models.Holding).filter(models.Holding.user_id == user.id).all()
    return {
        "user": user.email,
        "balance": user.balance,
        "holdings": [{"stock": h.stock_symbol, "quantity": h.quantity} for h in holdings]
    }
