import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService

from tests.tests_helpers import sign_in


def form_data(**overrides):
    data = {
        "title": "Waffles",
        "servings": "6",
        "tags": "Brunch",
        "ingredient_name[]": ["Flour", "Eggs"],
        "ingredient_quantity[]": ["3", "2"],
        "ingredient_unit[]": ["cups", ""],
        "steps": "Whisk\nCook",
    }
    data.update(overrides)
    return data


class EditRecipeWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([Recipe(
            id="r1", title="Pancakes", servings=4, tags={"Breakfast"},
            ingredients=[Ingredient("Flour", 2.0, "cups")], steps=["Mix", "Cook"],
        )])
        self.app = create_app(self.service)
        self.client = sign_in(self.app.test_client())
        self.url = "/recipes/r1/edit"

    def test_edit_page_is_prefilled(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in (b"Pancakes", b'value="4"', b"Breakfast", b"Flour", b"Mix\nCook"):
            self.assertIn(text, response.data)

    def test_valid_edit_updates_recipe_and_redirects_to_detail(self):
        response = self.client.post(self.url, data=form_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/recipes/r1"))
        recipe = self.service.get("r1")
        self.assertEqual(recipe.title, "Waffles")
        self.assertEqual(recipe.servings, 6)
        self.assertEqual(recipe.tags, {"Brunch"})
        self.assertEqual(recipe.steps, ["Whisk", "Cook"])
        self.assertEqual([(i.name, i.quantity, i.unit) for i in recipe.ingredients],
                         [("Flour", 3.0, "cups"), ("Eggs", 2.0, "")])
        self.assertEqual(len(self.service.list_recipes()), 1)

    def test_invalid_edit_leaves_recipe_unchanged(self):
        for bad in (form_data(title="  "), form_data(servings="0")):
            self.client.post(self.url, data=bad)
            self.assertEqual(self.service.get("r1").title, "Pancakes")
            self.assertEqual(self.service.get("r1").servings, 4)

    def test_unknown_recipe_is_404(self):
        self.assertEqual(self.client.get("/recipes/nope/edit").status_code, 404)
        self.assertEqual(self.client.post("/recipes/nope/edit", data=form_data()).status_code, 404)

    def test_detail_page_links_to_edit(self):
        self.assertIn(self.url.encode(), self.client.get("/recipes/r1").data)

    def test_edit_requires_login(self):
        response = self.app.test_client().get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
