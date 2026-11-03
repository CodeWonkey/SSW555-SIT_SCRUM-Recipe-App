import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


class FavoritesWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2, "cups")], ["Cook"], servings=2),
            Recipe("soup", "Tomato Soup", [Ingredient("Water", 500, "ml")], ["Simmer"], servings=4),
        ])
        self.users = UserService()
        self.user = self.users.register(name="Dad", email="dad@example.com", password="password-123")
        self.client = self.sign_in(self.user)

    def sign_in(self, user):
        client = create_app(self.service, self.users).test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.name
        return client

    def test_detail_page_offers_save_button(self):
        response = self.client.get("/recipes/pasta")
        self.assertIn(b"Save to Favorites", response.data)
        self.assertIn(b"/recipes/pasta/favorite", response.data)

    def test_saving_adds_recipe_to_saved_list(self):
        self.client.post("/recipes/pasta/favorite")
        self.assertEqual(self.user.favorites, ["pasta"])
        response = self.client.get("/favorites")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tomato Pasta", response.data)
        self.assertNotIn(b"Tomato Soup", response.data)

    def test_saved_recipe_shows_saved_state_instead_of_button(self):
        self.client.post("/recipes/pasta/favorite")
        response = self.client.get("/recipes/pasta")
        self.assertIn(b"Saved</button>", response.data)
        self.assertNotIn(b"Save to Favorites", response.data)

    def test_unsaved_recipe_still_offers_button_after_another_is_saved(self):
        self.client.post("/recipes/pasta/favorite")
        response = self.client.get("/recipes/soup")
        self.assertIn(b"Save to Favorites", response.data)

    def test_saving_twice_does_not_duplicate(self):
        self.client.post("/recipes/pasta/favorite")
        self.client.post("/recipes/pasta/favorite")
        self.assertEqual(self.user.favorites, ["pasta"])

    def test_saving_shows_confirmation_message(self):
        response = self.client.post("/recipes/pasta/favorite", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Saved to your favorites", response.data)

    def test_save_missing_recipe_returns_404(self):
        self.assertEqual(self.client.post("/recipes/missing/favorite").status_code, 404)
        self.assertEqual(self.user.favorites, [])

    def test_save_rejects_get_requests(self):
        self.assertEqual(self.client.get("/recipes/pasta/favorite").status_code, 405)

    def test_favorites_are_per_user(self):
        self.client.post("/recipes/pasta/favorite")
        other = self.users.register(name="Mom", email="mom@example.com", password="password-456")
        other_client = self.sign_in(other)
        self.assertNotIn(b"Tomato Pasta", other_client.get("/favorites").data)
        self.assertIn(b"Save to Favorites", other_client.get("/recipes/pasta").data)

    def test_deleted_recipe_disappears_from_saved_list(self):
        self.client.post("/recipes/pasta/favorite")
        self.service.delete("pasta")
        response = self.client.get("/favorites")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No saved recipes yet", response.data)

    def test_empty_saved_list_shows_empty_state(self):
        self.assertIn(b"No saved recipes yet", self.client.get("/favorites").data)

    def test_anonymous_visitor_is_redirected_to_login(self):
        anonymous = create_app(self.service, self.users).test_client()
        for method, path in (("post", "/recipes/pasta/favorite"), ("get", "/favorites")):
            with self.subTest(path=path):
                response = getattr(anonymous, method)(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()