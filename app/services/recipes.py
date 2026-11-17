from __future__ import annotations
import re
from math import isfinite
from typing import Iterable

# Re-export models to preserve existing service imports.
from app.models import Ingredient, Nutrition, Recipe, Review


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
        self._validate_nutrition(recipe.nutrition)
        self._recipes[recipe.id] = recipe
        return recipe

    def get(self, recipe_id: str) -> Recipe:
        try:
            return self._recipes[recipe_id]
        except KeyError as exc:
            raise RecipeNotFound(recipe_id) from exc

    def update(self, recipe_id: str, **changes: object) -> Recipe:
        recipe = self.get(recipe_id)
        allowed = {
            "title", "ingredients", "steps", "servings", "tags",
            "notes", "source_link", "nutrition", "diet_labels",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported recipe fields: {', '.join(sorted(unknown))}")
        title = changes.get("title", recipe.title)
        servings = changes.get("servings", recipe.servings)
        if not isinstance(title, str) or not title.strip() or not isinstance(servings, int) or servings < 1:
            raise ValueError("Recipe title and servings must be valid")
        self._validate_nutrition(changes.get("nutrition", recipe.nutrition))
        for name, value in changes.items():
            setattr(recipe, name, value)
        return recipe

    @staticmethod
    def _validate_nutrition(nutrition: object) -> None:
        if nutrition is not None and not isinstance(nutrition, Nutrition):
            raise ValueError("Nutrition must be a Nutrition object or None")

    def delete(self, recipe_id: str) -> None:
        self.get(recipe_id)
        del self._recipes[recipe_id]

    def search(self, query: str) -> list[Recipe]:
        needle = query.strip().casefold()
        if not needle:
            return self.list_recipes()
        return [r for r in self._recipes.values()
                if needle in r.title.casefold()
                or any(needle in item.name.casefold() for item in r.ingredients)
                or any(needle in step.casefold() for step in r.steps)
                or any(needle in tag.casefold() for tag in r.tags)]

    def filter(self, *, tag: str | None = None, favorites_only: bool = False) -> list[Recipe]:
        return [r for r in self._recipes.values()
                if (tag is None or tag.casefold() in {t.casefold() for t in r.tags})
                and (not favorites_only or r.favorite)]

    def set_favorite(self, recipe_id: str, favorite: bool = True) -> Recipe:
        recipe = self.get(recipe_id)
        recipe.favorite = favorite
        return recipe

    def set_cook_later(self, recipe_id: str, cook_later: bool = True) -> Recipe:
        recipe = self.get(recipe_id)
        recipe.cook_later = cook_later
        return recipe

    def cook_later_list(self) -> list[Recipe]:
        return [r for r in self._recipes.values() if r.cook_later]

    def rate(self, recipe_id: str, stars: int) -> Recipe:
        if not 1 <= stars <= 5: