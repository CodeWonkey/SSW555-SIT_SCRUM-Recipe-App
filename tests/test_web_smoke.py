import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService


class WebSmokeTests(unittest.TestCase):
    def test_home_page_renders_recipe_list(self):
        service = RecipeService([Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2, "cups")], ["Cook"], servings=2)])
        client = create_app(service).test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tomato Pasta", response.data)
        self.assertIn(b"styles.css", response.data)

    def test_empty_home_page_shows_empty_state(self):
        response = create_app(RecipeService()).test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your recipe box is ready", response.data)


if __name__ == "__main__":
    unittest.main()
