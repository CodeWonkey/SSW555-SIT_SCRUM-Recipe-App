import unittest

from app import create_app
from app.models import Ingredient, Recipe
from app.services.recipes import RecipeService
from tests.tests_helpers import sign_in


class ShareRecipeWebTests(unittest.TestCase):
    def setUp(self):
        self.recipe = Recipe(
            "r1", "Crêpes & berries", [Ingredient("flour", 1.5, "cups")],
            ["Mix flour & milk.", "Cook and serve."], servings=4,
            source_link="https://example.com/crepes", notes="Private family note",
        )
        self.service = RecipeService([
            self.recipe, Recipe("r2", "Other recipe", [], ["Other step"])
        ])
        self.app = create_app(self.service)
        self.client = sign_in(self.app.test_client())

    def test_share_is_available_from_recipe(self):
        response = self.client.get("/recipes/r1")
        self.assertIn(b'href="/recipes/r1/share"', response.data)
        self.assertIn(b">Share</a>", response.data)

    def test_share_offers_portable_text_and_download(self):
        response = self.client.get("/recipes/r1/share")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for expected in ("Crêpes &amp; berries", "Servings: 4", "1.5 cups flour",
                         "1. Mix flour &amp; milk.", "2. Cook and serve.",
                         "https://example.com/crepes", "/recipes/r1/share.txt",
                         "Copy recipe", "Share with an app", "readonly"):
            self.assertIn(expected, html)
        self.assertNotIn("Private family note", html)
        self.assertNotIn("Other step", html)

    def test_download_is_utf8_recipe_text_without_local_link(self):
        response = self.client.get("/recipes/r1/share.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.get_data(as_text=True),
                         "Crêpes & berries\nServings: 4\n\nIngredients\n"
                         "- 1.5 cups flour\n\nSteps\n1. Mix flour & milk.\n"
                         "2. Cook and serve.\n\nSource: https://example.com/crepes\n")
        self.assertNotIn(b"localhost", response.data)

    def test_sharing_uses_saved_amounts_and_does_not_change_recipe(self):
        response = self.client.get("/recipes/r1/share.txt?servings=8&units=metric")
        self.assertIn(b"Servings: 4", response.data)
        self.assertIn(b"1.5 cups flour", response.data)
        self.assertEqual(self.recipe.servings, 4)
        self.assertEqual(self.recipe.ingredients[0].quantity, 1.5)

    def test_share_text_is_escaped_on_page(self):
        self.recipe.title = '</textarea><script>alert("x")</script>'
        response = self.client.get("/recipes/r1/share")
        self.assertNotIn(b'<script>alert("x")</script>', response.data)
        self.assertIn(b"&lt;/textarea&gt;&lt;script&gt;", response.data)

    def test_recipe_without_source_can_be_shared(self):
        response = self.client.get("/recipes/r2/share.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Other recipe", response.data)
        self.assertNotIn(b"Source:", response.data)

    def test_missing_recipe_returns_404(self):
        for suffix in ("share", "share.txt"):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.client.get(f"/recipes/missing/{suffix}").status_code, 404)

    def test_sharing_requires_login(self):
        for suffix in ("share", "share.txt"):
            with self.subTest(suffix=suffix):
                response = self.app.test_client().get(f"/recipes/r1/{suffix}")
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.headers["Location"])
