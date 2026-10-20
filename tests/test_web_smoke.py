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

    def test_recipe_detail_page_displays_recipe_fields(self):
        recipe = Recipe(
            "pasta",
            "Tomato Pasta",
            [Ingredient("Tomato", 2, "cups"), Ingredient("Pasta", 1, "box")],
            ["Boil pasta", "Add tomatoes"],
            servings=2,
            tags={"Dinner", "Italian"},
            rating=5,
            source_link="https://example.com/tomato-pasta",
        )
        client = create_app(RecipeService([recipe])).test_client()

        response = client.get("/recipes/pasta")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tomato Pasta", response.data)
        self.assertIn(b"Tomato", response.data)
        self.assertIn(b"Pasta", response.data)
        self.assertIn(b"Boil pasta", response.data)
        self.assertIn(b"Add tomatoes", response.data)
        self.assertIn(b"2 servings", response.data)
        self.assertIn(b"Dinner", response.data)
        self.assertIn(b"Italian", response.data)
        self.assertIn(b"5", response.data)
        self.assertIn(b"https://example.com/tomato-pasta", response.data)

    def test_recipe_detail_page_returns_404_for_missing_recipe(self):
        client = create_app(RecipeService()).test_client()

        response = client.get("/recipes/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()