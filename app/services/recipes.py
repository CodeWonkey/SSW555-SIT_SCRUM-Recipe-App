from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Ingredient:
    name: str
    quantity: float
    unit: str = ""


@dataclass
class Recipe:
    id: str
    title: str
    ingredients: list[Ingredient]
    steps: list[str]
    servings: int = 1
    tags: set[str] = field(default_factory=set)
    favorite: bool = False
    rating: int | None = None
    notes: str = ""
    source_link: str = ""


class RecipeNotFound(KeyError):
    """Raised when a requested recipe ID is not in the service."""


class RecipeService:
    """Small in-memory service to give the team a testable starting point."""

    def __init__(self, recipes: Iterable[Recipe] = ()) -> None:
        self._recipes = {recipe.id: recipe for recipe in recipes}

    def list_recipes(self) -> list[Recipe]:
        return list(self._recipes.values())

    def create(self, recipe: Recipe) -> Recipe:
        if recipe.id in self._recipes:
            raise ValueError(f"Recipe ID already exists: {recipe.id}")
        if not recipe.title.strip():
            raise ValueError("Recipe title cannot be blank")
        if recipe.servings < 1:
            raise ValueError("Servings must be at least 1")
        self._recipes[recipe.id] = recipe
        return recipe

    def get(self, recipe_id: str) -> Recipe:
        try:
            return self._recipes[recipe_id]
        except KeyError as exc:
            raise RecipeNotFound(recipe_id) from exc

    def update(self, recipe_id: str, **changes: object) -> Recipe:
        recipe = self.get(recipe_id)
        allowed = {"title", "ingredients", "steps", "servings", "tags", "notes"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported recipe fields: {', '.join(sorted(unknown))}")
        title = changes.get("title", recipe.title)
        servings = changes.get("servings", recipe.servings)
        if not isinstance(title, str) or not title.strip() or not isinstance(servings, int) or servings < 1:
            raise ValueError("Recipe title and servings must be valid")
        for name, value in changes.items():
            setattr(recipe, name, value)
        return recipe

    def delete(self, recipe_id: str) -> None:
        self.get(recipe_id)
        del self._recipes[recipe_id]

    def search(self, query: str) -> list[Recipe]:
        needle = query.strip().casefold()
        if not needle:
            return self.list_recipes()
        return [r for r in self._recipes.values()
                if needle in r.title.casefold()
                or any(needle in item.name.casefold() for item in r.ingredients)]

    def filter(self, *, tag: str | None = None, favorites_only: bool = False) -> list[Recipe]:
        return [r for r in self._recipes.values()
                if (tag is None or tag.casefold() in {t.casefold() for t in r.tags})
                and (not favorites_only or r.favorite)]

    def set_favorite(self, recipe_id: str, favorite: bool = True) -> Recipe:
        recipe = self.get(recipe_id)
        recipe.favorite = favorite
        return recipe

    def rate(self, recipe_id: str, stars: int) -> Recipe:
        if not 1 <= stars <= 5:
            raise ValueError("Rating must be between 1 and 5 stars")
        recipe = self.get(recipe_id)
        recipe.rating = stars
        return recipe

    def scale_ingredients(self, recipe_id: str, target_servings: int) -> list[Ingredient]:
        recipe = self.get(recipe_id)
        if target_servings < 1:
            raise ValueError("Target servings must be at least 1")
        factor = target_servings / recipe.servings
        return [Ingredient(i.name, i.quantity * factor, i.unit) for i in recipe.ingredients]

    def shopping_items(self, recipe_ids: Iterable[str]) -> list[Ingredient]:
        """Combine same-name ingredients when their units match; preserve other units."""
        totals: dict[tuple[str, str], Ingredient] = {}
        for recipe_id in recipe_ids:
            for item in self.get(recipe_id).ingredients:
                key = (item.name.strip().casefold(), item.unit.strip().casefold())
                previous = totals.get(key)
                totals[key] = Ingredient(
                    previous.name if previous else item.name,
                    (previous.quantity if previous else 0) + item.quantity,
                    previous.unit if previous else item.unit,
                )
        return list(totals.values())

    def pantry_suggestions(self, pantry_names: Iterable[str]) -> list[tuple[Recipe, float, list[str]]]:
        """Return recipes ranked by exact normalized ingredient-name coverage."""
        pantry = {name.strip().casefold() for name in pantry_names}
        ranked = []
        for recipe in self._recipes.values():
            names = {ingredient.name.strip().casefold() for ingredient in recipe.ingredients}
            matched = names & pantry
            score = len(matched) / len(names) if names else 0.0
            missing = [ingredient.name for ingredient in recipe.ingredients
                       if ingredient.name.strip().casefold() not in pantry]
            ranked.append((recipe, score, missing))
        return sorted(ranked, key=lambda row: (-row[1], row[0].title.casefold()))
