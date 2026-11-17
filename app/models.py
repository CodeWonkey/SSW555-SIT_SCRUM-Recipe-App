"""Recipe data models shared by services and forms."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4
from math import isfinite


@dataclass(frozen=True)
class Ingredient:
    name: str
    quantity: float
    unit: str = ""


@dataclass(frozen=True)
class Nutrition:
    """Reported per-serving nutrition; None represents an unknown value."""

    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None

    def __post_init__(self) -> None:
        for value in (self.calories, self.protein, self.carbs, self.fat):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0
            ):
                raise ValueError("Nutrition values must be finite, non-negative numbers")

    @property
    def available(self) -> bool:
        return all(value is not None for value in
                   (self.calories, self.protein, self.carbs, self.fat))


@dataclass(frozen=True)
class Review:
    author_id: str
    author_name: str
    rating: int
    text: str
    id: str = field(default_factory=lambda: uuid4().hex)
    edited: bool = False


@dataclass
class Recipe:
    id: str
    title: str
    ingredients: list[Ingredient]
    steps: list[str]
    servings: int = 1
    tags: set[str] = field(default_factory=set)
    favorite: bool = False
    cook_later: bool = False
    rating: int | None = None
    notes: str = ""
    source_link: str = ""
    reviews: list[Review] = field(default_factory=list)
    nutrition: Nutrition | None = None
    diet_labels: set[str] = field(default_factory=set)
