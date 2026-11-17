from __future__ import annotations
import re
from dataclasses import replace
from math import isfinite
from typing import Iterable

# Re-export models to preserve existing service imports.
from app.models import Ingredient, Nutrition, Recipe, Review
_WORD = re.compile(r"\b\w+\b")
_FLAGGED_WORDS = frozenset({"stupid", "idiot"})

class RecipeNotFound(KeyError):
    """Raised when a requested recipe ID is not in the service."""


class ReviewNotFound(KeyError):
    """Raised when a review does not exist on the requested recipe."""


class ReviewPermissionDenied(PermissionError):
    """Raised when a user tries to change another author's review."""


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
        return [r for r in self._recipes.values() if self._matches(r, needle)]

    @staticmethod
    def _matches(recipe: Recipe, needle: str) -> bool:
        return (
            needle in recipe.title.casefold()
            or any(needle in item.name.casefold() for item in recipe.ingredients)
            or any(needle in step.casefold() for step in recipe.steps)
            or any(needle in tag.casefold() for tag in recipe.tags)
        )

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
            raise ValueError("Rating must be between 1 and 5 stars")
        recipe = self.get(recipe_id)
        recipe.rating = stars
        return recipe

    def add_review(
        self,
        recipe_id: str,
        author_id: str,
        author_name: str,
        rating: int,
        text: str,
    ) -> Review:
        recipe = self.get(recipe_id)
        clean_text = self._validate_review(rating, text)

        review = Review(
            author_id=author_id,
            author_name=author_name,
            rating=rating,
            text=clean_text,
        )

        recipe.reviews.append(review)
        return review

    @staticmethod
    def _validate_review(rating: int, text: str) -> str:
        clean_text = text.strip()
        if type(rating) is not int or not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        if not clean_text:
            raise ValueError("Review text cannot be empty.")
        if len(clean_text) > 1000:
            raise ValueError("Review must be 1000 characters or fewer.")
        if set(_WORD.findall(clean_text.casefold())) & _FLAGGED_WORDS:
            raise ValueError("Review contains flagged language.")
        return clean_text

    @staticmethod
    def _review_position(recipe: Recipe, review_id: str) -> int:
        """Locate a review once, or fail without changing the recipe."""
        for position, review in enumerate(recipe.reviews):
            if review.id == review_id:
                return position
        raise ReviewNotFound(review_id)

    def _author_review(self, recipe_id: str, review_id: str,
                       author_id: str, action: str) -> tuple[Recipe, int, Review]:
        """Reuse lookup and permission checks for editing and deleting."""
        recipe = self.get(recipe_id)
        position = self._review_position(recipe, review_id)
        review = recipe.reviews[position]
        if review.author_id != author_id:
            raise ReviewPermissionDenied(f"Only the author can {action} this review")
        return recipe, position, review

    def get_review(self, recipe_id: str, review_id: str) -> Review:
        recipe = self.get(recipe_id)
        return recipe.reviews[self._review_position(recipe, review_id)]

    def edit_review(self, recipe_id: str, review_id: str,
                    author_id: str, rating: int, text: str) -> Review:
        recipe, position, previous = self._author_review(
            recipe_id, review_id, author_id, "edit"
        )
        clean_text = self._validate_review(rating, text)
        updated = replace(previous, rating=rating, text=clean_text, edited=True)
        recipe.reviews[position] = updated
        return updated

    def delete_review(self, recipe_id: str, review_id: str, author_id: str) -> None:
        recipe, _position, review = self._author_review(
            recipe_id, review_id, author_id, "delete"
        )
        recipe.reviews = [item for item in recipe.reviews if item.id != review.id]

    def scale_ingredients(self, recipe_id: str, target_servings: int) -> list[Ingredient]:
        """Return quantities for a serving count without changing the saved recipe."""
        recipe = self.get(recipe_id)
        if type(target_servings) is not int or target_servings < 1:
            raise ValueError("Servings must be a whole number of at least 1")
        if type(recipe.servings) is not int or recipe.servings < 1:
            raise ValueError("The saved recipe must have a valid serving count")
        try:
            factor = target_servings / recipe.servings
            scaled = [Ingredient(i.name, i.quantity * factor, i.unit) for i in recipe.ingredients]
            if not isfinite(factor) or any(not isfinite(i.quantity) for i in scaled):
                raise ValueError("Scaled ingredient amounts must be finite")
        except OverflowError:
            raise ValueError("The serving count is too large to scale this recipe") from None
        return scaled

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

    def add_recipe_from_socials(self, recipe_id: str) -> Recipe:
        return self.set_favorite(recipe_id)
