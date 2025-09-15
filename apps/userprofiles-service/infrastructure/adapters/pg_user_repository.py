import os
import sys

import structlog
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from application.ports.user_repository import UserRepository
from domain.entities.user import User

logger = structlog.get_logger(__name__)


class PgUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository"""

    def __init__(self, db_pool: AsyncConnectionPool):
        self.db_pool = db_pool

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM userprofiles.get_user_by_id(%s)", (user_id,))
                row = await cur.fetchone()
                return self._row_to_user(row) if row else None

    async def get_by_cognito_sub(self, cognito_sub: str) -> User | None:
        """Get user by Cognito subject using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM userprofiles.get_user_by_sub(%s)", (cognito_sub,))
                row = await cur.fetchone()
                return self._row_to_user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM userprofiles.get_user_by_email(%s)", (email,))
                row = await cur.fetchone()
                return self._row_to_user(row) if row else None

    async def create(self, user: User) -> User:
        """Create new user using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM userprofiles.create_user(%s, %s, %s, %s, %s, %s)",
                    (
                        user.id,
                        user.cognito_sub,
                        user.email,
                        user.display_name,
                        user.avatar_url,
                        user.phone,
                    ),
                )
                row = await cur.fetchone()
                return self._row_to_user(row)

    async def update(self, user: User) -> User:
        """Update existing user using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM userprofiles.update_user(%s, %s, %s, %s, %s, %s)",
                    (
                        user.id,
                        user.email,
                        user.display_name,
                        user.avatar_url,
                        user.phone,
                        user.is_active,
                    ),
                )
                row = await cur.fetchone()
                if not row:
                    raise ValueError(f"User {user.id} not found for update")
                return self._row_to_user(row)

    async def delete(self, user_id: str) -> bool:
        """Delete user by ID using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM userprofiles.delete_user(%s)", (user_id,))
                result = await cur.fetchone()
                return result is not None

    async def list_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List active users with pagination using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM userprofiles.list_active_users(%s, %s)", (limit, offset))
                rows = await cur.fetchall()
                return [self._row_to_user(row) for row in rows]

    async def count_active_users(self) -> int:
        """Count active users using database function"""
        async with self.db_pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute("SELECT userprofiles.count_active_users()")
                row = await cur.fetchone()
                return row["count_active_users"] if row else 0

    def _row_to_user(self, row: dict) -> User:
        """Convert database row to User entity"""
        return User(
            id=str(row["id"]),
            cognito_sub=row["cognito_sub"],
            email=row["email"],
            display_name=row["display_name"],
            avatar_url=row["avatar_url"],
            phone=row["phone"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
