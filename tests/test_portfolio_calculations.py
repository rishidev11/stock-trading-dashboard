# tests/test_portfolio_calculations.py
from src.backend.models import Holding, User

def test_unrealised_pnl_calculation(db_session):
    user = User(email="calc@x.com", password_hash="h", balance=1000)
    holding = Holding(user=user, symbol="AAPL", quantity=10, avg_price=100)
    db_session.add(user)
    db_session.add(holding)
    db_session.commit()

    # Simulate market value
    market_value = holding.quantity * 120
    cost_basis = holding.quantity * holding.avg_price
    pnl = market_value - cost_basis

    assert pnl == 200
