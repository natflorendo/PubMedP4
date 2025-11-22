import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Iterable, List, Optional, Set

from psycopg import Connection
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import dotenv

"""
repository.py

Database wiring and user data access layer for PubMedFlo.
CRUD on users and role assignment and manages lifespan and pool connections.
"""

dotenv.load_dotenv()

DB_URL = os.getenv("PUBMEDFLO_DB_URL")

# A pool keeps a small set of open, reusable DB connections.
_pool: Optional[ConnectionPool] = None
ROLE_TABLES = {
    "admin": "admins",
    "curator": "curators",
    "end_user": "end_users",
}


def get_pool() -> ConnectionPool:
    """Lazily create a shared connection pool."""
    # Use the module level pool defined above.
    global _pool
    # First time running, create the pool and 
    # return everything from the DB as a dict (instead of a tuple).
    if _pool is None:
        # By default, psycopg_pool.ConnectionPool has min_size = 4
        # Use print(_pool.get_stats()) to verify
        _pool = ConnectionPool(conninfo=DB_URL, kwargs={"row_factory": dict_row})
    return _pool

# @asynccontextmanager turns this async def into an async context manager compatible with FastAPI’s lifespan parameter,
# which tells FastAPI how to manage startup and shutdown for this app.
@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan hook to open/close the connection pool."""
    pool = get_pool()
    pool.open() # before
    try:
        yield # during
    finally:
        pool.close() # after
        # Wait until all connections and background tasks are fully cleaned up before exit.
        pool.wait_close()


def get_db():
    """Provides a database connection from the pool."""
    pool = get_pool()
    # `with` means that the borrowed connection from the pool is always cleaned up once the block ends and 
    # if an error happens, the connection is still returned to the pool so no open connections leak.
    with pool.connection() as conn:
        yield conn


class UserRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def _roles_from_flags(self, row: Dict[str, Any]) -> List[str]:
        """Convert boolean role flags (is_admin, is_curator, is_end_user) from a DB row into a normalized list of role names."""
        roles: List[str] = []
        if row.pop("is_admin", False):
            roles.append("admin")
        if row.pop("is_curator", False):
            roles.append("curator")
        if row.pop("is_end_user", False):
            roles.append("end_user")
        # Default to ["end_user"] if none are set.
        if not roles:
            roles.append("end_user")
        return roles

    def _normalize_roles(self, roles: Optional[Iterable[str]]) -> List[str]:
        """Normalize a user-supplied iterable of role strings into a cleaned list of known roles."""
        # This is the list of valid roles we will return
        normalized: List[str] = []
        if roles:
            for role in roles:
                if not role:
                    continue
                key = role.strip().lower()
                if key in ROLE_TABLES and key not in normalized:
                    normalized.append(key)
        if not normalized:
            normalized.append("end_user")
        return normalized

    def _assign_roles(self, user_id: int, roles: Optional[Iterable[str]]) -> None:
        """Normalize the requested role names and synchronize this user's roles to the DB."""
        # Holds a set of valid role names for the user
        normalized: Set[str] = set(self._normalize_roles(roles))
        for role_name, table in ROLE_TABLES.items():
            # Insert user id to the relevant table given the role_name
            if role_name in normalized:
                self.conn.execute(
                    f"""
                    INSERT INTO {table} (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (user_id,),
                )
            else:
                # Delete any existing row for them in that role table
                self.conn.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))

    def _user_with_roles(
        self, where_clause: str, params: tuple, include_password: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single user matching the given WHERE clause, derive their roles from the role tables, and return a dict."""
        password_column = ", u.password_hash" if include_password else ""
        # Always select user_id, name, email, and created_at.
        # LEFT JOIN all the role tables to see what roles the user has.
        row = self.conn.execute(
            f"""
            SELECT
                u.user_id,
                u.name,
                u.email,
                u.created_at{password_column},
                adm.user_id IS NOT NULL AS is_admin,
                cur.user_id IS NOT NULL AS is_curator,
                eu.user_id IS NOT NULL AS is_end_user
            FROM users u
            LEFT JOIN admins adm ON adm.user_id = u.user_id
            LEFT JOIN curators cur ON cur.user_id = u.user_id
            LEFT JOIN end_users eu ON eu.user_id = u.user_id
            {where_clause}
            """,
            params,
        ).fetchone()
        if not row:
            return None
        # Convert the object to a dict (from tuple).
        record = dict(row)
        # Uses the boolean variables selected to make a list of roles.
        record["roles"] = self._roles_from_flags(record)
        return record

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._user_with_roles("WHERE u.email = %s", (email,))

    def get_user_auth_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._user_with_roles("WHERE u.email = %s", (email,), include_password=True)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._user_with_roles("WHERE u.user_id = %s", (user_id,))

    def list_users(self) -> List[Dict[str, Any]]:
        """
        Fetch all users and their roles and return a list of dicts with a normalized roles list for each user.
        """
        rows = self.conn.execute(
            """
            SELECT
                u.user_id,
                u.name,
                u.email,
                u.created_at,
                adm.user_id IS NOT NULL AS is_admin,
                cur.user_id IS NOT NULL AS is_curator,
                eu.user_id IS NOT NULL AS is_end_user
            FROM users u
            LEFT JOIN admins adm ON adm.user_id = u.user_id
            LEFT JOIN curators cur ON cur.user_id = u.user_id
            LEFT JOIN end_users eu ON eu.user_id = u.user_id
            ORDER BY u.user_id
            """
        ).fetchall()
        # List that holds all the user dicts.
        results: List[Dict[str, Any]] = []
        for entry in rows:
            # Convert the object to a dict (from tuple).
            record = dict(entry)
            # Uses the boolean variables selected to make a list of roles.
            record["roles"] = self._roles_from_flags(record)
            results.append(record)
        return results

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        roles: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new user record in the database and optionally assign roles."""
        user_row = self.conn.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING user_id, name, email, created_at
            """,
            (name, email, password_hash),
        ).fetchone()

        self._assign_roles(user_row["user_id"], roles)

        # Commits the transaction so the insert and role assignments are saved.
        self.conn.commit()

        # Fetches the full user record.
        return self.get_user_by_id(user_row["user_id"])

    # * = All parameters after this point must be passed by keyword, not by position.
    # * is a keyword-only seperator.
    def update_user(
        self,
        user_id: int,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        roles: Optional[Iterable[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing user's fields and/or roles. Roles are updated separately via `_assign_roles`."""
        # Assignments will hold the fields to update
        assignments: List[str] = []
        # params holds the values to those fields
        params: List[Any] = []
        if name is not None:
            assignments.append("name = %s")
            params.append(name)
        if email is not None:
            assignments.append("email = %s")
            params.append(email)
        if password_hash is not None:
            assignments.append("password_hash = %s")
            params.append(password_hash)

        # If we are only updating roles, make sure the user exists first.
        if not assignments and roles is not None:
            if not self.get_user_by_id(user_id):
                return None

        # Update if needed.
        if assignments:
            # * is Python’s unpacking (splat) operator.
            # *params means take each element of the list and pass it as its own positional item.
            updated = self.conn.execute(
                f"""
                UPDATE users
                SET {', '.join(assignments)}
                WHERE user_id = %s
                RETURNING user_id
                """,
                (*params, user_id),
            ).fetchone()
            # If no row, then no user matched. Undo work.
            if not updated:
                self.conn.rollback()
                return None

        if roles is not None:
            self._assign_roles(user_id, roles)

        # Commit both the user update and role updates.
        self.conn.commit()
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user from the database by user_id."""
        deleted = self.conn.execute(
            "DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,)
        ).fetchone()
        self.conn.commit()
        return bool(deleted)
