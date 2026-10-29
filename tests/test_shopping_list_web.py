import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService


class ShoppingListWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe(
                "pasta",
                "Tomato Pasta",
                [
                    Ingredient("Tomatoes", 2, "cups"),
                    Ingredient("Olive oil", 1, "tbsp"),
                ],
                ["Cook pasta"],
            ),
            Recipe(
                "soup",
                "Tomato Soup",
                [
                    Ingredient("tomatoes", 1, "cups"),
                    Ingredient("Water", 500, "ml"),
                ],
                ["Simmer"],
            ),
        ])
        self.app = create_app(self.service)
        self.client = self.app.test_client()

    def test_empty_shopping_list(self):
        response = self.client.get("/shopping-list")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your shopping list is empty.", response.data)

    def test_recipe_details_has_add_to_shopping_list_button(self):
        response = self.client.get("/recipes/pasta")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Add to Shopping List", response.data)
        self.assertIn(b"/recipes/pasta/shopping-list", response.data)

    def test_adding_recipe_adds_all_ingredients(self):
        response = self.client.post(
            "/recipes/pasta/shopping-list",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tomatoes", response.data)
        self.assertIn(b"Olive oil", response.data)
        self.assertIn(b"2 cups", response.data)
        self.assertIn(b"1 tbsp", response.data)

    def test_added_ingredients_are_unchecked(self):
        self.client.post("/recipes/pasta/shopping-list")
        response = self.client.get("/shopping-list")

        self.assertEqual(response.data.count(b'type="checkbox"'), 2)
        self.assertNotIn(b'checked="checked"', response.data)
        self.assertNotIn(b'type="checkbox" checked', response.data)

    def test_adding_same_recipe_twice_does_not_duplicate_ingredients(self):
        self.client.post("/recipes/pasta/shopping-list")
        self.client.post("/recipes/pasta/shopping-list")

        response = self.client.get("/shopping-list")

        self.assertEqual(response.data.count(b"Tomatoes"), 1)
        self.assertEqual(response.data.count(b"Olive oil"), 1)
        self.assertIn(b"2 cups Tomatoes", response.data)

    def test_matching_ingredients_from_different_recipes_are_combined(self):
        self.client.post("/recipes/pasta/shopping-list")
        self.client.post("/recipes/soup/shopping-list")

        response = self.client.get("/shopping-list")

        self.assertEqual(response.data.count(b"Tomatoes"), 1)
        self.assertIn(b"3 cups Tomatoes", response.data)
        self.assertIn(b"500 ml Water", response.data)

    def test_different_units_remain_separate(self):
        self.service.create(
            Recipe(
                "salad",
                "Tomato Salad",
                [Ingredient("Tomatoes", 200, "grams")],
                ["Mix"],
            )
        )

        self.client.post("/recipes/pasta/shopping-list")
        self.client.post("/recipes/salad/shopping-list")

        response = self.client.get("/shopping-list")

        self.assertIn(b"2 cups Tomatoes", response.data)
        self.assertIn(b"200 grams Tomatoes", response.data)

    def test_adding_nonexistent_recipe_returns_404(self):
        response = self.client.post("/recipes/missing/shopping-list")

        self.assertEqual(response.status_code, 404)

    def test_shopping_list_persists_across_navigation(self):
        self.client.post("/recipes/pasta/shopping-list")
        self.client.get("/")

        response = self.client.get("/shopping-list")

        self.assertIn(b"Tomatoes", response.data)
        self.assertIn(b"Olive oil", response.data)

    def test_deleted_recipe_is_handled(self):
        self.client.post("/recipes/pasta/shopping-list")
        self.service.delete("pasta")

        response = self.client.get("/shopping-list")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your shopping list is empty.", response.data)


if __name__ == "__main__":
    unittest.main()