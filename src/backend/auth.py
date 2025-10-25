from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import backend.models as models
from passlib.context import CryptContext
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import get_db

# secret key used for testing purposes
# TODO: Put in environment variable
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserLogin(BaseModel):
    email: str
    password: str


# Hash a plain text password for secure storage
def get_password_hash(password: str):
    return pwd_context.hash(password)

@router.get("/test")
def test():
    return {"message": "Auth router working!"}


# New user registration endpoint
@router.post("/register")
def register_user(user:UserLogin, db: Session = Depends(get_db)):
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(email=user.email, password_hash=hashed_pw, balance=100000.0)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered", "user_id": db_user.id}


# Login endpoint
@router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(db_user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


security = HTTPBearer()

# Retrieve user data from database based off user information
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials  # Extract the actual token
    try:
        payload = jwt.decode(token, SECRET_KEY, [ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    db_user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return db_user

