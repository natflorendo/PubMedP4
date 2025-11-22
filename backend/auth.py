import os
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from .models import AuthResponse, TokenPayload, UserCreate, UserOut
from .repository import UserRepository, get_db

"""
auth.py

Authentication and authorization helpers for PubMedFlo.
Also has signin/login and user validation routes and returns an AuthResponse based on JWT.
"""

# Key used to sign JWT tokens.
SECRET_KEY = os.getenv("PUBMEDFLO_SECRET")
# JWT signing algorithm.
ALGORITHM = os.getenv("PUBMEDFLO_JWT_ALGORITHM")
# How long the access tokens should be valid.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("PUBMEDFLO_TOKEN_TTL"))

router = APIRouter()
# Creates a password hashing context using bcrypt, which handles hashing and verifying passwords.
# `deprecated="auto"`` means older hashes (e.g., different algorithm) are still accepted but flagged internally.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Tells FastAPI that tokens are retrieved from a login endpoint located at /login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a plain password with a stored hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain password with password hashing algorithm."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Creates a new JWT containing the provided data"""
    # dict contains sub (user id) and roles.
    # copy dict to avoid modifying (it just in case it's every used somewhere else). 
    to_encode = data.copy()
    # Use env TTL by defaut to calculat ethe expiration time.
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    # Encode the payload with the secret key and signing algorithm.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Depends(x) means run x first and plug its return value into this parameter automatically.
def get_current_user(
    token: str = Depends(oauth2_scheme), conn=Depends(get_db)
) -> dict:
    """Authenticates a request using a Bearer JWT"""
    # Variable that holds an exception that can be reused for bad/expired tokens.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Try to decode the payload, retrieve the data into a Pydantic model, then store the `sub` as an int.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # `**`` is a dictionary unpacking operator. It means “take all the key–value pairs in 
        # this dict and pass them as keyword arguments.
        token_data = TokenPayload(**payload)
        user_id = int(token_data.sub)
    # Catch any error with the token or `sub` conversion
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Try to get user and return error if there is no matching user_id.
    repo = UserRepository(conn)
    user = repo.get_user_by_id(user_id)
    if not user:
        raise credentials_exception
    # Returns the entire user dict
    return user

# Just used for admin.py right now.
def require_roles(roles: Iterable[str]) -> Callable:
    """Used for role-based authentication."""
    # Normalize required roles to lowercase.
    required = {role.lower() for role in roles}

    def checker(user=Depends(get_current_user)) -> dict:
        # Should already be all lower case, but done just in case.
        user_roles = {r.lower() for r in user.get("roles", [])}
        # `intersection` gives roles that appear in both sets.
        if not user_roles.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have the required role",
            )
        return user
    # Return user dict.
    return checker

# `response_model=AuthResponse` is the structure the response should be.
# `status_code=201` sets the default HTTP status
@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, conn=Depends(get_db)):
    # Connect to db.
    repo = UserRepository(conn)
    existing = repo.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed = get_password_hash(payload.password)
    user_record = repo.create_user(payload.name, payload.email, hashed, payload.roles)
    access_token = create_access_token(
        data={"sub": str(user_record["user_id"]), "roles": user_record["roles"]}
    )
    # `**`` is a dictionary unpacking operator. It means “take all the key–value pairs in 
    # this dict and pass them as keyword arguments.
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserOut(**user_record),
    }

# OAuth2PasswordRequestForm will parse a form-encoded body (not JSON) that contains a username and password.
@router.post("/login", response_model=AuthResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), conn=Depends(get_db)
):
    repo = UserRepository(conn)
    user_record = repo.get_user_auth_by_email(form_data.username)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Compare plain text password to the stored hashed password
    if not verify_password(form_data.password, user_record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(
        data={"sub": str(user_record["user_id"]), "roles": user_record["roles"]}
    )
    # Create a dictionary from the user_record (not including password_hash)
    user_payload = {k: v for k, v in user_record.items() if k != "password_hash"}
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserOut(**user_payload),
    }

# Lets the frontend fetch the currently logged in user from the token
@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return UserOut(**current_user)
