import unittest
from io import BytesIO

from bs4 import BeautifulSoup
from pypdf import PdfReader
from werkzeug.http import parse_options_header

from app import create_app
from app.models import Ingredient, Recipe
from app.services.recipes import RecipeService
from tests.tests_helpers import sign_in


class RecipePdfWebTests(unittest.TestCase):
    def setUp(self):
        self.recipe = Recipe(
            "r1", "Crêpes & berries", [Ingredient("crème fraîche", 1.5, "cups"),
                                      Ingredient("eggs", 2)],
            ["Whisk until lumps are < ½ cm.", "Fold in ⅓ of the berries."], servings=4,
        )
        self.app = create_app(RecipeService([self.recipe]))
        self.client = sign_in(self.app.test_client())

    def test_download_from_recipe_page(self):
        page = self.client.get("/recipes/r1?servings=8&units=metric")
        link = BeautifulSoup(page.data, "html.parser").find("a", string="Export as PDF")
        self.assertIsNotNone(link)
        response = self.client.get(link["href"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        disposition, options = parse_options_header(response.headers["Content-Disposition"])
        self.assertEqual(disposition, "attachment")
        self.assertTrue(options["filename"].endswith(".pdf"))
        pdf = PdfReader(BytesIO(response.data))
        self.assertEqual(len(pdf.pages), 1)
        content = pdf.pages[0].extract_text()
        expected = [self.recipe.title, "Servings: 4", "Ingredients", "1.5 cups crème fraîche",
                    "2 eggs", "Instructions", "1.", self.recipe.steps[0], "2.", self.recipe.steps[1]]
        offset = 0
        for entry in expected:
            with self.subTest(entry=entry):
                self.assertIn(entry, content[offset:])
                offset = content.index(entry, offset) + len(entry)

    def test_long_instruction_continues_across_pages(self):
        self.recipe.steps = ["Stir gently. " * 900 + "Remove from heat.", "Serve warm."]
        response = self.client.get("/recipes/r1/export.pdf")
        pdf = PdfReader(BytesIO(response.data))
        self.assertGreater(len(pdf.pages), 1)
        text = " ".join(" ".join(page.extract_text().split()) for page in pdf.pages)
        self.assertEqual(text.count("Stir gently."), 900)
        self.assertIn("Remove from heat.", text)
        self.assertIn("Serve warm.", pdf.pages[-1].extract_text())

    def test_login_and_recipe_lookup_apply_to_download(self):
        response = self.app.test_client().get("/recipes/r1/export.pdf")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(self.client.get("/recipes/missing/export.pdf").status_code, 404)
