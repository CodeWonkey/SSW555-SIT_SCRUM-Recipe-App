import unittest

from app import create_app
from app.services.recipes import Ingredient, Nutrition, Recipe, RecipeService
from tests.test_add_recipe_web import form_data
from tests.tests_helpers import sign_in


class NutritionServiceTests(unittest.TestCase):
    def test_unknown_and_partial_nutrition_are_unavailable(self):
        self.assertFalse(Nutrition().available)
        for missing in ("calories", "protein", "carbs", "fat"):
            values = dict(calories=200, protein=10, carbs=25, fat=5)
            values[missing] = None
            self.assertFalse(Nutrition(**values).available)

    def test_zero_is_available(self):
        self.assertTrue(Nutrition(0, 0, 0, 0).available)

    def test_invalid_values_rejected_for_each_macro(self):
        for field in ("calories", "protein", "carbs", "fat"):
            for invalid in (-1, float("nan"), float("inf"), float("-inf"), "10", True):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    Nutrition(**{field: invalid})

    def test_create_read_update_clear_and_preserve_nutrition(self):
        service = RecipeService()
        service.create(Recipe("r1", "Soup", [], [], nutrition=Nutrition(200, 10, 25, 5)))
        self.assertEqual(service.get("r1").nutrition.calories, 200)
        service.update("r1", title="New soup")
        self.assertEqual(service.get("r1").nutrition.protein, 10)
        service.update("r1", nutrition=Nutrition(300, 20, 30, 6))
        self.assertEqual(service.get("r1").nutrition.fat, 6)
        with self.assertRaises(ValueError):
            service.update("r1", title="Invalid change", nutrition={"calories": 100})
        self.assertEqual(service.get("r1").title, "New soup")
        service.update("r1", nutrition=None)
        self.assertIsNone(service.get("r1").nutrition)


class NutritionWebTests(unittest.TestCase):
    def setUp(self):
        self.recipe = Recipe("r1", "Soup", [Ingredient("Carrots", 2)], ["Simmer"],
                             servings=2, nutrition=Nutrition(250, 12.5, 30, 8))
        self.service = RecipeService([self.recipe])
        self.app = create_app(self.service)
        self.app.config["TESTING"] = True
        self.client = sign_in(self.app.test_client())

    def test_detail_displays_all_macros_with_units_and_recipe_content(self):
        response = self.client.get("/recipes/r1")
        self.assertEqual(response.status_code, 200)
        for text in ("Per serving", "Calories", "250 kcal", "Protein", "12.5 g",
                     "Carbs", "30 g", "Fat", "8 g", "Ingredients", "Carrots", "Steps", "Simmer"):
            self.assertIn(text.encode(), response.data)
        self.assertNotIn(b"Nutrition info unavailable", response.data)

    def test_missing_empty_and_partial_nutrition_show_message_without_blank_fields(self):
        for nutrition in (None, Nutrition(), Nutrition(calories=250)):
            with self.subTest(nutrition=nutrition):
                self.recipe.nutrition = nutrition
                response = self.client.get("/recipes/r1")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Nutrition info unavailable", response.data)
                self.assertNotIn(b"<dt>", response.data)
                self.assertIn(b"Simmer", response.data)

    def test_zero_macros_render_as_numbers(self):
        self.recipe.nutrition = Nutrition(0, 0, 0, 0)
        response = self.client.get("/recipes/r1")
        self.assertIn(b"0 kcal", response.data)
        self.assertEqual(response.data.count(b"<dd>0 g</dd>"), 3)
        self.assertNotIn(b"unavailable", response.data)

    def test_add_form_supports_optional_macros(self):
        response = self.client.get("/recipes/add")
        for name in ("calories", "protein", "carbs", "fat"):
            self.assertIn(f'name="{name}"'.encode(), response.data)
        response = self.client.post("/recipes/add", data=form_data(
            calories="250", protein="12.5", carbs="30", fat="8"))
        self.assertEqual(response.status_code, 302)
        recipe = self.service.list_recipes()[-1]
        self.assertEqual(recipe.nutrition, Nutrition(250, 12.5, 30, 8))
        self.assertIn(b"12.5 g", self.client.get(f"/recipes/{recipe.id}").data)

    def test_add_without_macros_shows_unavailable(self):
        self.client.post("/recipes/add", data=form_data(calories="", protein="", carbs="", fat=""))
        recipe = self.service.list_recipes()[-1]
        self.assertIsNone(recipe.nutrition)
        self.assertIn(b"Nutrition info unavailable", self.client.get(f"/recipes/{recipe.id}").data)

    def test_invalid_macro_submission_never_creates_or_changes_recipe(self):
        for invalid in ("-1", "NaN", "inf", "abc", ""):
            data = form_data(calories=invalid, protein="10", carbs="20", fat="5")
            for url in ("/recipes/add", "/recipes/r1/edit"):
                with self.subTest(invalid=invalid, url=url):
                    response = self.client.post(url, data=data)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b"flash-danger", response.data)
                    self.assertIn(b'value="10"', response.data)
                    self.assertEqual(len(self.service.list_recipes()), 1)
                    self.assertEqual(self.recipe.title, "Soup")
                    self.assertEqual(self.recipe.nutrition, Nutrition(250, 12.5, 30, 8))

    def test_edit_prefills_updates_and_clears_macros(self):
        response = self.client.get("/recipes/r1/edit")
        self.assertIn(b'value="12.5"', response.data)
        response = self.client.post("/recipes/r1/edit", data=form_data(
            calories="300", protein="15", carbs="40", fat="0"), follow_redirects=True)
        self.assertIn(b"300 kcal", response.data)
        self.assertEqual(self.recipe.nutrition, Nutrition(300, 15, 40, 0))
        response = self.client.post("/recipes/r1/edit", data=form_data(
            calories="", protein="", carbs="", fat=""), follow_redirects=True)
        self.assertIn(b"Nutrition info unavailable", response.data)
        self.assertIsNone(self.recipe.nutrition)

    def test_legacy_edit_without_nutrition_fields_preserves_macros(self):
        self.client.post("/recipes/r1/edit", data=form_data())
        self.assertEqual(self.recipe.nutrition, Nutrition(250, 12.5, 30, 8))

    def test_missing_recipe_and_login_requirements_still_apply(self):
        self.assertEqual(self.client.get("/recipes/missing").status_code, 404)
        response = self.app.test_client().get("/recipes/r1")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
