from datetime import UTC, datetime
from typing import List, Optional

from app.domain.models.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.storage.sqlite import get_sqlite


class SQLiteUserRepository(UserRepository):
    async def create_user(self, user: User) -> User:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                    user_id, fullname, email, password_hash, role, is_active, created_at, updated_at, last_login_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.fullname,
                    user.email,
                    user.password_hash,
                    user.role.value,
                    int(user.is_active),
                    user.created_at.isoformat(),
                    user.updated_at.isoformat(),
                    user.last_login_at.isoformat() if user.last_login_at else None,
                ),
            )
            await conn.commit()
        return user

    def _row_to_user(self, row) -> User:
        return User.model_validate(
            {
                "id": row["user_id"],
                "fullname": row["fullname"],
                "email": row["email"],
                "password_hash": row["password_hash"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_login_at": row["last_login_at"],
            }
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return self._row_to_user(row) if row else None

    async def get_user_by_fullname(self, fullname: str) -> Optional[User]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE fullname = ?", (fullname,))
            row = await cursor.fetchone()
            return self._row_to_user(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
            row = await cursor.fetchone()
            return self._row_to_user(row) if row else None

    async def update_user(self, user: User) -> User:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                UPDATE users
                SET fullname = ?, email = ?, password_hash = ?, role = ?, is_active = ?, updated_at = ?, last_login_at = ?
                WHERE user_id = ?
                """,
                (
                    user.fullname,
                    user.email,
                    user.password_hash,
                    user.role.value,
                    int(user.is_active),
                    user.updated_at.isoformat(),
                    user.last_login_at.isoformat() if user.last_login_at else None,
                    user.id,
                ),
            )
            await conn.commit()
        return user

    async def delete_user(self, user_id: str) -> bool:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await conn.commit()
            return cursor.rowcount > 0

    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def fullname_exists(self, fullname: str) -> bool:
        return await self.get_user_by_fullname(fullname) is not None

    async def email_exists(self, email: str) -> bool:
        return await self.get_user_by_email(email) is not None
