import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


class RateRecipeWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2, "cups")], ["Cook"], servings=2),
            Recipe("soup", "Tomato Soup", [Ingredient("Water", 500, "ml")], ["Simmer"], servings=4),
        ])
        self.users = UserService()
        self.user = self.users.register(name="Sam", email="sam@example.com", password="password-123")
        self.app = create_app(self.service, self.users)
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user.id
            sess["user_name"] = self.user.name

    def rate(self, stars, recipe_id="pasta", follow=False):
        return self.client.post(
            f"/recipes/{recipe_id}/rate", data={"stars": stars}, follow_redirects=follow
        )

    def test_detail_page_offers_rating_form(self):
        response = self.client.get("/recipes/pasta")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/recipes/pasta/rate", response.data)
        self.assertIn(b'name="stars"', response.data)

    def test_valid_rating_is_saved(self):
        self.rate("4")
        self.assertEqual(self.service.get("pasta").rating, 4)

    def test_saved_rating_is_shown_on_the_recipe(self):
        response = self.rate("4", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rating: 4/5", response.data)
        self.assertIn(b"Rated recipe 4/5 stars", response.data)

    def test_saved_rating_is_shown_in_the_recipe_list(self):
        self.rate("4")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b"Rating: 4/5"), 1)

    def test_unrated_recipes_show_no_rating(self):
        self.assertNotIn(b"Rating:", self.client.get("/").data)
        self.assertNotIn(b"Rating:", self.client.get("/recipes/pasta").data)

    def test_rating_one_recipe_does_not_rate_the_others(self):
        self.rate("5")
        self.assertIsNone(self.service.get("soup").rating)

    def test_current_rating_is_preselected_in_the_form(self):
        self.rate("3")
        response = self.client.get("/recipes/pasta")
        self.assertIn(b'value="3" selected', response.data)

    def test_rating_can_be_changed(self):
        self.rate("2")
        self.rate("5")
        self.assertEqual(self.service.get("pasta").rating, 5)

    def test_invalid_ratings_are_rejected(self):
        for bad in ("0", "6", "-1", "3.5", "abc", ""):
            with self.subTest(stars=bad):
                response = self.rate(bad, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"between 1 and 5", response.data)
                self.assertIsNone(self.service.get("pasta").rating)

    def test_invalid_rating_keeps_the_existing_one(self):
        self.rate("4")
        self.rate("9")
        self.assertEqual(self.service.get("pasta").rating, 4)

    def test_rate_missing_recipe_returns_404(self):
        self.assertEqual(self.rate("5", recipe_id="missing").status_code, 404)

    def test_rate_rejects_get_requests(self):
        self.assertEqual(self.client.get("/recipes/pasta/rate").status_code, 405)

    def test_anonymous_visitor_is_redirected_to_login(self):
        anonymous = self.app.test_client()
        response = anonymous.post("/recipes/pasta/rate", data={"stars": "5"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertIsNone(self.service.get("pasta").rating)


if __name__ == "__main__":
    unittest.main()