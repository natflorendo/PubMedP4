from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import errors

from .auth import get_password_hash, require_roles
from .models import UserOut, UserUpdate
from .repository import UserRepository, get_db

"""
admin.py

Admin-only FastAPI routes for managing users. Has access to list, update, or delete users.
"""

# `prefix` adds the given prefix to every route inside this router.
# `tags` adds an Swagger tag for documentation. (Use http://127.0.0.1:8000/docs)
# `dependencies` adds a router level dependency that runs for every endpoint in this router.
# It requires the admin role to use these routes.
# Depends(x) means run x first and plug its return value into this parameter automatically.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(["admin"]))],
)


# `response_model=UserOut` means FastAPI will validate the returned data using the UserOut schema.
@router.get("/users", response_model=list[UserOut])
def list_users(conn=Depends(get_db)):
    """Returns all raw user dicts from the DB."""
    repo = UserRepository(conn)
    # `**`` is a dictionary unpacking operator. It means “take all the key–value pairs in 
    # this dict and pass them as keyword arguments.
    # Uses list_users from repository.py
    return [UserOut(**row) for row in repo.list_users()]


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, conn=Depends(get_db)):
    """Update a user's fields and/or roles and return the updated user."""
    repo = UserRepository(conn)
    hashed = get_password_hash(payload.password) if payload.password else None

    try:
        # Anything being None means it won't update
        updated = repo.update_user(
            user_id,
            name=payload.name,
            email=payload.email,
            password_hash=hashed,
            roles=payload.roles,
        )
    # Check for if user is trying to change to an email already in use.
    except errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
        )
    

    # If None is returned, that means the user wasn't found or nothing could be updated.
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserOut(**updated)

# `status_code=204` sets the default HTTP status
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, conn=Depends(get_db)):
    """Delete a user by ID."""
    repo = UserRepository(conn)
    success = repo.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
