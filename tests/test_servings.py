import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeNotFound, RecipeService
from tests.tests_helpers import sign_in


def sample_recipe():
    return Recipe("r1", "Bread", [
        Ingredient("Flour", 1, "cup"),
        Ingredient("Water", 0.75, "cup"),
        Ingredient("Yeast", 0.25, "tsp"),
        Ingredient("Eggs", 2),
        Ingredient("Salt", 0, "tsp"),
    ], ["Mix and bake"], servings=4)


class ServingServiceTests(unittest.TestCase):
    def setUp(self):
        self.recipe = sample_recipe()
        self.service = RecipeService([self.recipe])

    def test_every_amount_doubles_from_four_to_eight(self):
        scaled = self.service.scale_ingredients("r1", 8)
        self.assertEqual([i.quantity for i in scaled], [2, 1.5, 0.5, 4, 0])
        self.assertEqual([(i.name, i.unit) for i in scaled],
                         [(i.name, i.unit) for i in self.recipe.ingredients])

    def test_repeated_scaling_always_uses_saved_amounts(self):
        original = list(self.recipe.ingredients)
        for servings, factor in ((8, 2), (2, 0.5), (1, 0.25), (4, 1), (3, 0.75)):
            scaled = self.service.scale_ingredients("r1", servings)
            for saved, ingredient in zip(original, scaled):
                self.assertAlmostEqual(ingredient.quantity, saved.quantity * factor)
        self.assertEqual(self.recipe.ingredients, original)
        self.assertEqual(self.recipe.servings, 4)

    def test_invalid_counts_are_rejected(self):
        for count in (0, -1, True, False, 1.5, "8", None, float("inf"), float("nan"), 10**400):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.service.scale_ingredients("r1", count)

    def test_invalid_saved_count_does_not_divide_by_zero(self):
        for count in (0, -1, True, 1.5):
            self.recipe.servings = count
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.service.scale_ingredients("r1", 8)

    def test_nonfinite_scaled_amounts_are_rejected(self):
        self.recipe.ingredients = [Ingredient("Flour", 1e308, "g")]
        with self.assertRaises(ValueError):
            self.service.scale_ingredients("r1", 8)

    def test_empty_ingredients_and_unknown_recipe(self):
        self.recipe.ingredients = []
        self.assertEqual(self.service.scale_ingredients("r1", 8), [])
        with self.assertRaises(RecipeNotFound):
            self.service.scale_ingredients("missing", 8)


class ServingWebTests(unittest.TestCase):
    def setUp(self):
        self.recipe = sample_recipe()
        self.service = RecipeService([self.recipe])
        self.app = create_app(self.service)
        self.app.config["TESTING"] = True
        self.client = sign_in(self.app.test_client())

    def page(self, query=""):
        response = self.client.get("/recipes/r1" + query)
        return response, " ".join(response.get_data(as_text=True).split())

    def test_default_controls_and_amounts(self):
        response, html = self.page()
        self.assertEqual(response.status_code, 200)
        for text in ('method="GET"', 'name="servings"', 'value="4"',
                     'min="1" step="1" required', "1 cup Flour", "0.75 cup Water",
                     "Update servings", "Reset to 4", "js/servings.js"):
            self.assertIn(text, html)

    def test_four_to_eight_doubles_all_displayed_amounts(self):
        response, html = self.page("?servings=8")
        self.assertEqual(response.status_code, 200)
        for text in ('value="8"', "8 servings", "2 cup Flour", "1.5 cup Water",
                     "0.5 tsp Yeast", "4 Eggs", "0 tsp Salt", "Mix and bake"):
            self.assertIn(text, html)
        self.assertEqual(self.recipe.servings, 4)
        self.assertEqual(self.recipe.ingredients, sample_recipe().ingredients)

    def test_halving_reset_and_independent_visitors(self):
        _, html = self.page("?servings=2")
        self.assertIn("0.5 cup Flour", html)
        self.assertIn("0.375 cup Water", html)
        _, html = self.page()
        self.assertIn("1 cup Flour", html)
        other = sign_in(self.app.test_client())
        self.assertIn(b'value="4"', other.get("/recipes/r1").data)

    def test_invalid_requests_show_error_with_original_amounts(self):
        for value in ("0", "-1", "1.5", "abc", "", "NaN", "inf", "9" * 400):
            with self.subTest(value=value):
                response, html = self.page("?servings=" + value)
                self.assertEqual(response.status_code, 400)
                self.assertIn('role="alert"', html)
                self.assertIn('aria-invalid="true"', html)
                self.assertIn("1 cup Flour", html)
                self.assertIn('value="4"', html)
                self.assertEqual(self.recipe.servings, 4)

    def test_missing_recipe_and_authentication(self):
        self.assertEqual(self.client.get("/recipes/missing?servings=8").status_code, 404)
        response = self.app.test_client().get("/recipes/r1?servings=8")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_script_is_served(self):
        self.assertEqual(self.client.get("/static/js/servings.js").status_code, 200)
