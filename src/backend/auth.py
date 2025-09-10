from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
import backend.models as models
from passlib.context import CryptContext
from pydantic import BaseModel
import bcrypt

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UserLogin(BaseModel):
    email: str
    password: str


@router.get("/test")
def test():
    return {"message": "Auth router working!"}


@router.post("/register")
def register_user(user:UserLogin, db: Session = Depends(get_db)):
    hashed_pw = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, password_hash=hashed_pw, balance=100000.0)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered", "user_id": db_user.id}


@router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": db_user.id}
