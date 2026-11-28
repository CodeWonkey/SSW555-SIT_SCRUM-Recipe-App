import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


class PersonalNotesWebTests(unittest.TestCase):
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
            name="Dad",
            email="dad@example.com",
            password="password-123",
        )
        self.client = self.sign_in(self.user)

    def sign_in(self, user):
        client = create_app(self.service, self.users).test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.name
        return client

    def test_saved_recipe_displays_personal_notes_form(self):
        self.client.post("/recipes/pasta/favorite")

        response = self.client.get("/recipes/pasta")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Personal Notes", response.data)
        self.assertIn(b"/recipes/pasta/personal-note", response.data)

    def test_unsaved_recipe_does_not_display_notes_form(self):
        response = self.client.get("/recipes/pasta")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Personal Notes", response.data)

    def test_user_can_save_and_revisit_note(self):
        self.client.post("/recipes/pasta/favorite")

        response = self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Add extra garlic next time."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Add extra garlic next time.", response.data)
        self.assertEqual(
            self.user.personal_notes["pasta"],
            "Add extra garlic next time.",
        )

        revisit = self.client.get("/recipes/pasta")
        self.assertIn(b"Add extra garlic next time.", revisit.data)

    def test_user_can_update_existing_note(self):
        self.client.post("/recipes/pasta/favorite")

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Use less salt."},
        )

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Use more basil."},
        )

        self.assertEqual(
            self.user.personal_notes["pasta"],
            "Use more basil.",
        )

        response = self.client.get("/recipes/pasta")
        self.assertIn(b"Use more basil.", response.data)
        self.assertNotIn(b"Use less salt.", response.data)

    def test_user_can_clear_existing_note(self):
        self.client.post("/recipes/pasta/favorite")

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Try adding cheese."},
        )

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": ""},
        )

        self.assertNotIn("pasta", self.user.personal_notes)

    def test_notes_are_private_to_each_user(self):
        self.client.post("/recipes/pasta/favorite")

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Dad's secret recipe tip."},
        )

        other = self.users.register(
            name="Mom",
            email="mom@example.com",
            password="password-456",
        )

        other_client = self.sign_in(other)
        other_client.post("/recipes/pasta/favorite")

        response = other_client.get("/recipes/pasta")

        self.assertNotIn(b"Dad&#39;s secret recipe tip.", response.data)
        self.assertNotIn(b"Dad's secret recipe tip.", response.data)
        self.assertEqual(other.personal_notes, {})

    def test_unsaved_recipe_rejects_personal_note(self):
        response = self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Should not be saved."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.personal_notes, {})
        self.assertIn(b"Recipe must be saved", response.data)

    def test_missing_recipe_returns_404(self):
        response = self.client.post(
            "/recipes/missing/personal-note",
            data={"personal_note": "Test note"},
        )

        self.assertEqual(response.status_code, 404)

    def test_get_request_cannot_save_note(self):
        response = self.client.get("/recipes/pasta/personal-note")

        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_cannot_save_note(self):
        anonymous = create_app(self.service, self.users).test_client()

        response = anonymous.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "Unauthorized note"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(self.user.personal_notes, {})

    def test_note_exceeding_limit_is_rejected(self):
        self.client.post("/recipes/pasta/favorite")

        response = self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "A" * 2001},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.personal_notes, {})
        self.assertIn(b"2000 characters or fewer", response.data)

    def test_note_is_escaped_in_html(self):
        self.client.post("/recipes/pasta/favorite")

        self.client.post(
            "/recipes/pasta/personal-note",
            data={"personal_note": "<script>alert('test')</script>"},
        )

        response = self.client.get("/recipes/pasta")

        self.assertNotIn(b"<script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)


if __name__ == "__main__":
    unittest.main()