import unittest
from datetime import datetime, timezone, timedelta

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


class CookingHistoryTests(unittest.TestCase):

    def setUp(self):
        self.recipe1 = Recipe(
            id="recipe-1",
            title="Pasta",
            ingredients=[Ingredient("Pasta", 200, "g")],
            steps=["Boil pasta"],
            servings=2,
        )

        self.recipe2 = Recipe(
            id="recipe-2",
            title="Pizza",
            ingredients=[Ingredient("Flour", 300, "g")],
            steps=["Bake pizza"],
            servings=4,
        )

        self.recipes = RecipeService([self.recipe1, self.recipe2])
        self.users = UserService()

        self.app = create_app(self.recipes, self.users)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        self.user = self.users.register(
            name="Test User",
            email="test@example.com",
            password="Password123!",
        )

        with self.client.session_transaction() as session:
            session["user_id"] = self.user.id
            session["user_name"] = self.user.name

    def test_empty_history(self):
        response = self.client.get("/cooking-history")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You haven't marked any recipes as cooked yet.",
            response.get_data(as_text=True),
        )

    def test_mark_recipe_as_cooked(self):
        response = self.client.post("/recipes/recipe-1/cooked")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/cooking-history", response.location)
        self.assertEqual(len(self.user.cooking_history), 1)
        self.assertEqual(
            self.user.cooking_history[0].recipe_id,
            "recipe-1",
        )

    def test_history_displays_recipe(self):
        self.client.post("/recipes/recipe-1/cooked")

        response = self.client.get("/cooking-history")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Pasta", html)
        self.assertIn("Cooked on", html)

    def test_history_newest_first(self):
        older = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
        newer = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

        self.users.mark_recipe_cooked(
            self.user.id,
            "recipe-1",
            older,
        )

        self.users.mark_recipe_cooked(
            self.user.id,
            "recipe-2",
            newer,
        )

        response = self.client.get("/cooking-history")
        html = response.get_data(as_text=True)

        self.assertLess(
            html.index("Pizza"),
            html.index("Pasta"),
        )

    def test_same_recipe_can_be_cooked_multiple_times(self):
        self.client.post("/recipes/recipe-1/cooked")
        self.client.post("/recipes/recipe-1/cooked")

        self.assertEqual(len(self.user.cooking_history), 2)

    def test_history_is_user_specific(self):
        other_user = self.users.register(
            name="Other User",
            email="other@example.com",
            password="Password123!",
        )

        self.users.mark_recipe_cooked(
            self.user.id,
            "recipe-1",
        )

        self.assertEqual(
            self.users.get_cooking_history(other_user.id),
            [],
        )

    def test_deleted_recipe_does_not_break_history(self):
        self.client.post("/recipes/recipe-1/cooked")
        self.recipes.delete("recipe-1")

        response = self.client.get("/cooking-history")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You haven't marked any recipes as cooked yet.",
            response.get_data(as_text=True),
        )

    def test_nonexistent_recipe_cannot_be_marked_cooked(self):
        response = self.client.post("/recipes/missing/cooked")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(self.user.cooking_history), 0)

    def test_cooking_history_requires_login(self):
        self.client.post("/logout")

        response = self.client.get("/cooking-history")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_recipe_detail_has_mark_as_cooked_button(self):
        response = self.client.get("/recipes/recipe-1")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Mark as Cooked", html)
        self.assertIn(
            '/recipes/recipe-1/cooked',
            html,
        )


if __name__ == "__main__":
    unittest.main()