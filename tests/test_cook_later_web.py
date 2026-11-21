import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


class CookLaterWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe(
                "pasta",
                "Tomato Pasta",
                [Ingredient("Tomato", 2, "cups")],
                ["Cook"],
                servings=2,
            ),
            Recipe(
                "soup",
                "Tomato Soup",
                [Ingredient("Water", 500, "ml")],
                ["Simmer"],
                servings=4,
            ),
        ])

        self.users = UserService()
        self.user = self.users.register(
            name="Alice",
            email="alice@example.com",
            password="password-123",
        )
        self.client = self.sign_in(self.user)

    def sign_in(self, user):
        client = create_app(self.service, self.users).test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.name
        return client

    def test_detail_page_offers_cook_later_button(self):
        response = self.client.get("/recipes/pasta")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b">Cook Later</button>", response.data)
        self.assertIn(b"/recipes/pasta/cook-later", response.data)

    def test_saving_adds_recipe_to_cook_later_list(self):
        response = self.client.post("/recipes/pasta/cook-later")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.user.cook_later, ["pasta"])

        response = self.client.get("/cook-later")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tomato Pasta", response.data)
        self.assertNotIn(b"Tomato Soup", response.data)

    def test_saved_recipe_shows_added_state(self):
        self.client.post("/recipes/pasta/cook-later")

        response = self.client.get("/recipes/pasta")

        self.assertIn(b"Added to Cook Later", response.data)
        self.assertNotIn(b">Cook Later</button>", response.data)

    def test_other_recipe_still_offers_button(self):
        self.client.post("/recipes/pasta/cook-later")

        response = self.client.get("/recipes/soup")

        self.assertIn(b">Cook Later</button>", response.data)

    def test_saving_twice_does_not_duplicate(self):
        self.client.post("/recipes/pasta/cook-later")
        self.client.post("/recipes/pasta/cook-later")

        self.assertEqual(self.user.cook_later, ["pasta"])

    def test_saving_shows_confirmation_message(self):
        response = self.client.post(
            "/recipes/pasta/cook-later",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Recipe added to your cook-later list.",
            response.data,
        )

    def test_missing_recipe_returns_404(self):
        response = self.client.post("/recipes/missing/cook-later")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.user.cook_later, [])

    def test_save_rejects_get_requests(self):
        response = self.client.get("/recipes/pasta/cook-later")

        self.assertEqual(response.status_code, 405)

    def test_cook_later_lists_are_per_user(self):
        self.client.post("/recipes/pasta/cook-later")

        other = self.users.register(
            name="Bob",
            email="bob@example.com",
            password="password-456",
        )
        other_client = self.sign_in(other)

        response = other_client.get("/cook-later")

        self.assertNotIn(b"Tomato Pasta", response.data)
        self.assertEqual(other.cook_later, [])
        self.assertIn(
            b">Cook Later</button>",
            other_client.get("/recipes/pasta").data,
        )

    def test_deleted_recipe_does_not_appear_in_list(self):
        self.client.post("/recipes/pasta/cook-later")
        self.service.delete("pasta")

        response = self.client.get("/cook-later")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recipes saved for later yet.", response.data)

    def test_empty_list_shows_empty_state(self):
        response = self.client.get("/cook-later")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recipes saved for later yet.", response.data)

    def test_anonymous_visitor_is_redirected_to_login(self):
        anonymous = create_app(self.service, self.users).test_client()

        for method, path in (
            ("post", "/recipes/pasta/cook-later"),
            ("get", "/cook-later"),
        ):
            with self.subTest(path=path):
                response = getattr(anonymous, method)(path)

                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.headers["Location"])

        self.assertEqual(self.user.cook_later, [])

    def test_favorites_and_cook_later_are_independent(self):
        self.client.post("/recipes/pasta/cook-later")

        self.assertEqual(self.user.cook_later, ["pasta"])
        self.assertEqual(self.user.favorites, [])

        self.client.post("/recipes/soup/favorite")

        self.assertEqual(self.user.cook_later, ["pasta"])
        self.assertEqual(self.user.favorites, ["soup"])

    def test_navigation_contains_cook_later_link(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/cook-later"', response.data)


if __name__ == "__main__":
    unittest.main()