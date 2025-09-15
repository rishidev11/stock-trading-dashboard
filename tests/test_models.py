# tests/test_models.py
from src.backend import models

def test_user_model(db_session):
    user = models.User(email="user@x.com", password_hash="hash", balance=1000)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "user@x.com"
    assert user.balance == 1000
