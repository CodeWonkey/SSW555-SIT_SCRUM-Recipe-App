import unittest

from flask import url_for

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService


def make_service():
    return RecipeService([
        Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2, "cups")], ["Cook"], servings=2),
        Recipe("soup", "Tomato Soup", [Ingredient("Water", 500, "ml")], ["Simmer"], servings=4),
    ])


class DeleteRecipeWebTests(unittest.TestCase):
    def setUp(self):
        self.service = make_service()
        self.app = create_app(self.service)
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user"
            sess["user_name"] = "Test"
        with self.app.test_request_context():
            self.delete_url = url_for("main.delete_recipe", recipe_id="pasta")
            self.detail_url = url_for("main.recipe_detail", recipe_id="pasta")
            self.missing_url = url_for("main.delete_recipe", recipe_id="missing")

    def test_detail_page_has_delete_form(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.delete_url.encode(), response.data)
        self.assertIn(b"Delete recipe", response.data)

    def test_delete_removes_recipe_from_service(self):
        self.client.post(self.delete_url)
        self.assertEqual([r.id for r in self.service.list_recipes()], ["soup"])

    def test_delete_redirects_to_list_without_the_recipe(self):
        response = self.client.post(self.delete_url, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.detail_url.encode(), response.data)
        self.assertIn(b"Tomato Soup", response.data)

    def test_deleted_recipe_can_no_longer_be_opened(self):
        self.client.post(self.delete_url)
        self.assertEqual(self.client.get(self.detail_url).status_code, 404)

    def test_delete_shows_confirmation_message(self):
        response = self.client.post(self.delete_url, follow_redirects=True)
        self.assertIn(b"Deleted", response.data)

    def test_delete_missing_recipe_returns_404(self):
        self.assertEqual(self.client.post(self.missing_url).status_code, 404)
        self.assertEqual(len(self.service.list_recipes()), 2)

    def test_delete_rejects_get_requests(self):
        self.assertEqual(self.client.get(self.delete_url).status_code, 405)
        self.assertEqual(len(self.service.list_recipes()), 2)

    def test_delete_requires_login(self):
        anonymous = self.app.test_client()
        response = anonymous.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(len(self.service.list_recipes()), 2)

    def test_deleted_recipe_is_dropped_from_shopping_list(self):
        self.client.post(f"/recipes/pasta/shopping-list")
        self.client.post(self.delete_url)
        response = self.client.get("/shopping-list")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your shopping list is empty", response.data)


if __name__ == "__main__":
    unittest.main()