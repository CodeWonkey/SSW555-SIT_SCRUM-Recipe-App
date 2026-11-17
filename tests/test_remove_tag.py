"""US-26: Remove a category tag from a recipe.

Each saved tag on the edit form has an x button. Removing that tag and
saving drops it from the recipe. The other tags and the rest of the recipe
stay as they were.
"""

import re
import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService

from tests.tests_helpers import sign_in


def form_data(**overrides):
    data = {
        "title": "Pancakes",
        "servings": "4",
        "tags": "Easy",
        "ingredient_name[]": ["Flour"],
        "ingredient_quantity[]": ["2"],
        "ingredient_unit[]": ["cups"],
        "steps": "Mix\nCook",
    }
    data.update(overrides)
    return data


def remove_buttons(html):
    """Buttons that remove one category tag and do not submit the form."""
    found = {}
    for opening, mark in re.findall(
        r"(<button\b[^>]*>)\s*([×x])\s*</button>",
        html,
    ):
        if 'type="button"' not in opening:
            continue
        label = re.search(r'aria-label="Remove tag ([^"]+)"', opening)
        if label:
            found[label.group(1)] = mark
    return found


class RemoveTagTests(unittest.TestCase):
    def setUp(self):
        self.recipe = Recipe(
            id="r1",
            title="Pancakes",
            servings=4,
            tags={"Breakfast", "Easy"},
            ingredients=[Ingredient("Flour", 2.0, "cups")],
            steps=["Mix", "Cook"],
        )
        self.service = RecipeService([self.recipe])
        self.client = sign_in(create_app(self.service).test_client())

    def test_edit_page_offers_an_x_for_each_tag(self):
        html = self.client.get("/recipes/r1/edit").get_data(as_text=True)

        self.assertEqual(remove_buttons(html), {"Breakfast": "×", "Easy": "×"})

    def test_removing_one_tag_and_saving_drops_only_that_tag(self):
        response = self.client.post("/recipes/r1/edit", data=form_data())

        self.assertEqual(response.status_code, 302)
        recipe = self.service.get("r1")
        self.assertEqual(recipe.tags, {"Easy"})
        self.assertEqual(recipe.title, "Pancakes")
        self.assertEqual([(item.name, item.quantity, item.unit) for item in recipe.ingredients],
                         [("Flour", 2.0, "cups")])

        detail = self.client.get("/recipes/r1").get_data(as_text=True)
        listing = self.client.get("/").get_data(as_text=True)
        edit = self.client.get("/recipes/r1/edit").get_data(as_text=True)
        for page in (detail, listing):
            self.assertIn("Pancakes", page)
            self.assertIn("Easy", page)
            self.assertNotIn("Breakfast", page)
        self.assertIn("Pancakes", edit)
        self.assertEqual(remove_buttons(edit), {"Easy": "×"})

    def test_removing_every_tag_leaves_the_recipe_open(self):
        response = self.client.post("/recipes/r1/edit", data=form_data(tags=""))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.service.get("r1").tags, set())

        detail = self.client.get("/recipes/r1")
        edit = self.client.get("/recipes/r1/edit").get_data(as_text=True)
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Pancakes", detail.get_data(as_text=True))
        self.assertEqual(remove_buttons(edit), {})
