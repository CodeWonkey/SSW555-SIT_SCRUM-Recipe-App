import json
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from app import create_app
from app.services.recipes import RecipeService
from tests.tests_helpers import sign_in


SOURCE_URL = "https://example.com/toast"
RECIPE_HTML = '<script type="application/ld+json">' + json.dumps({
    "@type": "Recipe",
    "name": "Simple Toast",
    "recipeIngredient": ["2 slices bread", "1 tablespoon butter"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Toast the bread."}],
    "recipeYield": "2 servings",
    "keywords": "Breakfast, Easy",
}) + '</script>'


class RecipeImportWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService()
        self.app = create_app(self.service)
        self.app.config["TESTING"] = True
        self.client = sign_in(self.app.test_client())

    def test_import_page_and_home_link(self):
        response = self.client.get("/recipes/import")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="source_url"', response.data)
        self.assertIn(b'href="/recipes/import"', self.client.get("/").data)

    @patch("app.routes.fetch_recipe_html")
    def test_import_requires_login_before_downloading(self, fetch):
        client = self.app.test_client()
        for method in (client.get, client.post):
            response = method("/recipes/import")
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login", response.headers["Location"])
        fetch.assert_not_called()

    @patch("app.routes.fetch_recipe_html", return_value=RECIPE_HTML)
    def test_import_opens_editable_review_without_saving(self, fetch):
        response = self.client.post("/recipes/import", data={"source_url": SOURCE_URL})
        self.assertEqual(response.status_code, 200)
        fetch.assert_called_once_with(SOURCE_URL)
        self.assertEqual(self.service.list_recipes(), [])
        page = BeautifulSoup(response.data, "html.parser")
        self.assertEqual(page.h2.text, "Review imported recipe")
        form = page.find("form", class_="recipe-form")
        self.assertEqual(form["action"], "/recipes/add")
        for name, expected in {
            "title": "Simple Toast", "servings": "2", "source_link": SOURCE_URL,
            "tags": "Breakfast, Easy", "_imported": "1",
        }.items():
            self.assertEqual(form.find("input", attrs={"name": name})["value"], expected)
        names = form.find_all("input", attrs={"name": "ingredient_name[]"})
        self.assertEqual([item["value"] for item in names],
                         ["2 slices bread", "1 tablespoon butter"])
        quantities = form.find_all("input", attrs={"name": "ingredient_quantity[]"})
        self.assertEqual([item["value"] for item in quantities], ["", ""])
        self.assertEqual(form.find("textarea", attrs={"name": "steps"}).text,
                         "Toast the bread.")
        self.assertIn(b"Save recipe", response.data)
        self.assertNotIn(b"Save changes", response.data)

    @patch("app.routes.fetch_recipe_html", return_value=RECIPE_HTML)
    def test_review_saves_user_edits_without_another_download(self, fetch):
        response = self.client.post("/recipes/import", data={"source_url": SOURCE_URL})
        form = BeautifulSoup(response.data, "html.parser").find("form", class_="recipe-form")
        data = {}
        for field in form.find_all("input", attrs={"name": True}):
            if field["name"].endswith("[]"):
                data.setdefault(field["name"], []).append(field.get("value", ""))
            else:
                data[field["name"]] = field.get("value", "")
        data.update({
            "title": "My Toast",
            "ingredient_name[]": ["bread", "butter"],
            "ingredient_quantity[]": ["2", "1"],
            "ingredient_unit[]": ["slices", "tablespoon"],
            "steps": "Toast the bread.\nSpread butter.",
        })
        saved = self.client.post(form["action"], data=data)
        self.assertEqual(saved.status_code, 302)
        fetch.assert_called_once_with(SOURCE_URL)
        recipe, = self.service.list_recipes()
        self.assertEqual(recipe.title, "My Toast")
        self.assertEqual(recipe.source_link, SOURCE_URL)
        self.assertEqual(recipe.servings, 2)
        self.assertEqual(recipe.steps, ["Toast the bread.", "Spread butter."])
        self.assertEqual([(i.name, i.quantity, i.unit) for i in recipe.ingredients],
                         [("bread", 2.0, "slices"), ("butter", 1.0, "tablespoon")])

    @patch("app.routes.fetch_recipe_html", side_effect=ValueError("The website returned HTTP 403."))
    def test_download_failure_stays_on_import_form_with_url_and_error(self, fetch):
        response = self.client.post("/recipes/import", data={"source_url": SOURCE_URL})
        self.assertEqual(response.status_code, 400)
        page = BeautifulSoup(response.data, "html.parser")
        self.assertEqual(page.find(attrs={"role": "alert"}).text,
                         "The website returned HTTP 403.")
        self.assertEqual(page.find("input", attrs={"name": "source_url"})["value"], SOURCE_URL)
        self.assertEqual(self.service.list_recipes(), [])

    @patch("app.routes.fetch_recipe_html", return_value="<html>No recipe</html>")
    def test_unsupported_page_shows_error_without_saving(self, fetch):
        response = self.client.post("/recipes/import", data={"source_url": SOURCE_URL})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"No supported recipe metadata", response.data)
        self.assertEqual(self.service.list_recipes(), [])

    def test_invalid_url_shows_error_including_empty_submission(self):
        for url in ("", "not a URL", "ftp://example.com", "https://name:password@example.com"):
            with self.subTest(url=url):
                response = self.client.post("/recipes/import", data={"source_url": url})
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'role="alert"', response.data)
                self.assertEqual(self.service.list_recipes(), [])

    def test_failed_review_save_preserves_edited_fields(self):
        response = self.client.post("/recipes/add", data={
            "_imported": "1", "title": "", "servings": "2",
            "source_link": SOURCE_URL, "tags": "Breakfast",
            "ingredient_name[]": ["bread"], "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["slices"], "steps": "Toast the bread.",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Review imported recipe", response.data)
        self.assertIn(b"Recipe title cannot be blank", response.data)
        self.assertIn(SOURCE_URL.encode(), response.data)
        self.assertIn(b'value="bread"', response.data)
        self.assertIn(b"Toast the bread.", response.data)
        self.assertEqual(self.service.list_recipes(), [])

    def test_invalid_nutrition_preserves_import_review_and_does_not_save(self):
        response = self.client.post("/recipes/add", data={
            "_imported": "1", "title": "My Toast", "servings": "2",
            "source_link": SOURCE_URL, "tags": "Breakfast",
            "ingredient_name[]": ["bread"], "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["slices"], "steps": "Toast the bread.",
            "calories": "invalid", "protein": "10", "carbs": "20", "fat": "5",
        })
        self.assertEqual(response.status_code, 200)
        page = BeautifulSoup(response.data, "html.parser")
        self.assertEqual(page.h2.text, "Review imported recipe")
        self.assertIn(b"flash-danger", response.data)
        self.assertEqual(page.find("input", attrs={"name": "title"})["value"], "My Toast")
        self.assertEqual(page.find("input", attrs={"name": "source_link"})["value"], SOURCE_URL)
        self.assertEqual(page.find("input", attrs={"name": "protein"})["value"], "10")
        self.assertIn(b"Toast the bread.", response.data)
        self.assertEqual(self.service.list_recipes(), [])
