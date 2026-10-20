from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Iterable

from werkzeug.security import check_password_hash, generate_password_hash

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str


class UserService:
    """In-memory accounts. Passwords are stored only as hashes."""

    def __init__(self, users: Iterable[User] = ()) -> None:
        self._by_email: dict[str, User] = {}
        self._by_id: dict[str, User] = {}
        for user in users:
            self._store(user)

    def register(self, *, name: str, email: str, password: str) -> User:
        clean_name = name.strip()
        clean_email = email.strip()
        if not clean_name:
            raise ValueError("Name is required")
        if not _EMAIL.fullmatch(clean_email):
            raise ValueError("Enter a valid email address")
        if not password:
            raise ValueError("Password is required")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if self.get_by_email(clean_email) is not None:
            raise ValueError("An account with this email already exists")

        user = User(
            id=uuid.uuid4().hex[:8],
            name=clean_name,
            email=clean_email,
            password_hash=generate_password_hash(password),
        )
        self._store(user)
        return user

    def get(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email.strip().casefold())

    def password_matches(self, user: User, password: str) -> bool:
        return check_password_hash(user.password_hash, password)

    def _store(self, user: User) -> None:
        self._by_email[user.email.casefold()] = user
        self._by_id[user.id] = user
