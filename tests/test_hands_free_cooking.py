"""US-37: recipe steps can be followed without a mouse or microphone."""
import unittest
from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class HandsFreeCookingTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe("soup", "Soup", [], ["Chop carrots", "Simmer", "Serve"]),
            Recipe("empty", "Empty", [], []),
        ])
        self.app = create_app(self.service)
        self.client = sign_in(self.app.test_client())

    def test_recipe_links_to_cooking_mode(self):
        html = self.client.get("/recipes/soup").get_data(as_text=True)
        self.assertIn("Start hands-free cooking", html)
        self.assertIn("/recipes/soup/cook", html)

    def test_steps_and_buttons_render(self):
        response = self.client.get("/recipes/soup/cook")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Step 1 of 3", html)
        self.assertIn("Chop carrots", html)
        self.assertIn("Simmer", html)
        self.assertIn("Serve", html)
        self.assertIn("Previous step", html)
        self.assertIn("Next step", html)
        self.assertIn("Enable voice commands", html)
        self.assertIn("cook_mode.js", html)

    def test_no_steps_works(self):
        response = self.client.get("/recipes/empty/cook")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"does not have any cooking steps", response.data)

    def test_bad_id_returns_404(self):
        self.assertEqual(self.client.get("/recipes/missing/cook").status_code, 404)

    def test_login_required(self):
        response = self.app.test_client().get("/recipes/soup/cook")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_step_text_escaped(self):
        self.service.get("soup").steps.append("<script>alert(1)</script>")
        response = self.client.get("/recipes/soup/cook")
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>alert(1)</script>", response.data)

if __name__ == "__main__":
    unittest.main()
