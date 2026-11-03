from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from werkzeug.security import check_password_hash, generate_password_hash

from app.services.meal_plan import add_recipe, empty_plan

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

# Value is what we store. Label is what the profile shows.
DIETARY_RESTRICTIONS = (
    ("vegetarian", "Vegetarian"),
    ("gluten-free", "Gluten-free"),
    ("dairy-free", "Dairy-free"),
    ("vegan", "Vegan"),
)
# Milk and wheat are covered by the dairy-free and gluten-free choices above.
ALLERGIES = (
    ("peanuts", "Peanuts"),
    ("tree-nuts", "Tree nuts"),
    ("shellfish", "Shellfish"),
    ("eggs", "Eggs"),
    ("soy", "Soy"),
    ("sesame", "Sesame"),
)
_ALLOWED_RESTRICTIONS = {value for value, _label in DIETARY_RESTRICTIONS}
_ALLOWED_ALLERGIES = {value for value, _label in ALLERGIES}
_ALLERGY_LABELS = {label.casefold(): value for value, label in ALLERGIES}
_MAX_ALLERGY_LENGTH = 40


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str
    dietary_restrictions: set[str] = field(default_factory=set)
    allergies: set[str] = field(default_factory=set)
    other_allergies: set[str] = field(default_factory=set)
    meal_plan: dict[str, list[str]] = field(default_factory=empty_plan)


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

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.get_by_email(email)
        if user is not None and self.password_matches(user, password):
            return user
        return None

    def password_matches(self, user: User, password: str) -> bool:
        return check_password_hash(user.password_hash, password)

    def update_dietary_restrictions(self, user_id: str, restrictions: Iterable[str]) -> User:
        """Replace this account's dietary restrictions with the given choices.

        An empty selection clears them. Unknown choices are rejected and the
        previously saved set is left unchanged. Allergies are not changed.
        """
        user = self.get(user_id)
        if user is None:
            raise ValueError("Account not found")

        user.dietary_restrictions = self._clean_choices(
            restrictions, _ALLOWED_RESTRICTIONS, "dietary restriction"
        )
        return user

    def update_profile_preferences(
        self,
        user_id: str,
        restrictions: Iterable[str],
        allergies: Iterable[str],
        other_allergies: str = "",
    ) -> User:
        """Replace dietary restrictions and allergies together.

        Validation runs before anything is saved, so an invalid choice leaves
        the account unchanged. A typed allergy that matches a checkbox is stored
        as that checkbox instead of a second custom entry.
        """
        user = self.get(user_id)
        if user is None:
            raise ValueError("Account not found")

        cleaned_restrictions = self._clean_choices(
            restrictions, _ALLOWED_RESTRICTIONS, "dietary restriction"
        )
        cleaned_allergies = self._clean_choices(allergies, _ALLOWED_ALLERGIES, "allergy")
        cleaned_allergies, cleaned_other = self._clean_other_allergies(
            other_allergies, cleaned_allergies
        )
        user.dietary_restrictions = cleaned_restrictions
        user.allergies = cleaned_allergies
        user.other_allergies = cleaned_other
        return user

    def _clean_choices(self, selected: Iterable[str], allowed: set[str], kind: str) -> set[str]:
        cleaned: set[str] = set()
        for raw in selected:
            key = raw.strip().casefold()
            if not key:
                continue
            if key not in allowed:
                raise ValueError(f"Unsupported {kind}: {raw.strip()}")
            cleaned.add(key)
        return cleaned

    def _clean_other_allergies(self, raw: str, selected: set[str]) -> tuple[set[str], set[str]]:
        extras: dict[str, str] = {}
        for piece in raw.split(","):
            text = " ".join(piece.split())
            if not text:
                continue
            if len(text) > _MAX_ALLERGY_LENGTH:
                raise ValueError(f"Each allergy must be {_MAX_ALLERGY_LENGTH} characters or fewer")
            key = text.casefold()
            if key in _ALLOWED_ALLERGIES:
                selected.add(key)
                continue
            if key in _ALLERGY_LABELS:
                selected.add(_ALLERGY_LABELS[key])
                continue
            extras.setdefault(key, text)
        return selected, set(extras.values())

    def assign_meal(self, user_id: str, day: str, recipe_id: str) -> User:
        """Assign a saved recipe to one day of this account's weekly plan."""
        user = self.get(user_id)
        if user is None:
            raise ValueError("Account not found")
        user.meal_plan = add_recipe(user.meal_plan, day, recipe_id)
        return user

    def _store(self, user: User) -> None:
        self._by_email[user.email.casefold()] = user
        self._by_id[user.id] = user
