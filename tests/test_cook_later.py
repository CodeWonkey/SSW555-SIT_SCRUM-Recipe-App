"""US-22: Add a recipe to a cook-later list.

Acceptance criteria covered:
- adding a recipe once places it on the cook-later list
- adding the same recipe again does not duplicate it
- removing the mark takes it off the list without deleting the recipe
- marking a missing recipe raises RecipeNotFound
"""

import pytest

from app.services.recipes import Ingredient, Recipe, RecipeNotFound, RecipeService


def make_recipe(recipe_id="r1", title="Pancakes"):
    return Recipe(
        id=recipe_id,
        title=title,
        ingredients=[Ingredient("flour", 2, "cups")],
        steps=["Mix", "Cook"],
    )


def test_add_recipe_to_cook_later_list():
    service = RecipeService([make_recipe()])
    updated = service.set_cook_later("r1", True)
    assert updated.cook_later is True
    assert [r.id for r in service.cook_later_list()] == ["r1"]


def test_adding_twice_does_not_duplicate():
    service = RecipeService([make_recipe()])
    service.set_cook_later("r1", True)
    service.set_cook_later("r1", True)
    assert [r.id for r in service.cook_later_list()] == ["r1"]


def test_remove_from_cook_later_keeps_recipe():
    service = RecipeService([make_recipe()])
    service.set_cook_later("r1", True)
    service.set_cook_later("r1", False)
    assert service.cook_later_list() == []
    # the recipe itself is untouched
    assert service.get("r1").title == "Pancakes"


def test_cook_later_missing_recipe_raises():
    service = RecipeService()
    with pytest.raises(RecipeNotFound):
        service.set_cook_later("nope", True)
