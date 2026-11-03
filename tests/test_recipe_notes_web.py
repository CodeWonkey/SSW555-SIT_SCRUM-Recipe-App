
import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class RecipeNotesWebTests(unittest.TestCase):

    def setUp(self):
        self.service = RecipeService([
            Recipe("r1", "Pancakes", [], ["Mix", "Cook"]),
            Recipe("r2", "Pasta", [], ["Boil"]),
        ])
        self.app = create_app(self.service)
        self.client = sign_in(self.app.test_client())

    def test_add_notes(self):
        response = self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Use less sugar"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.service.get("r1").notes,
            "Use less sugar"
        )

    def test_notes_visible_after_refresh(self):
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Add extra cinnamon"}
        )
        response = self.client.get("/recipes/r1")
        self.assertIn(b"Add extra cinnamon", response.data)

    def test_edit_notes(self):
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Original note"}
        )
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Updated note"}
        )
        self.assertEqual(
            self.service.get("r1").notes,
            "Updated note"
        )

    def test_clear_notes(self):
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Old note"}
        )
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": ""}
        )
        self.assertEqual(self.service.get("r1").notes, "")

    def test_notes_stay_with_correct_recipe(self):
        self.client.post(
            "/recipes/r1/notes",
            data={"notes": "Pancake tip"}
        )
        self.assertEqual(self.service.get("r2").notes, "")

    def test_missing_recipe_returns_404(self):
        response = self.client.post(
            "/recipes/unknown/notes",
            data={"notes": "Test"}
        )
        self.assertEqual(response.status_code, 404)

    def test_notes_require_login(self):
        client = self.app.test_client()
        response = client.post(
            "/recipes/r1/notes",
            data={"notes": "Test"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
