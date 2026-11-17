import unittest

from app.services.measurement_conversion import convert_to_metric
from app.services.recipes import Ingredient, Recipe, RecipeService


class MeasurementConversionTests(unittest.TestCase):

    def test_cups_to_milliliters(self):
        ingredients = [Ingredient("Milk", 2, "cups")]

        result = convert_to_metric(ingredients)

        self.assertEqual(result[0].quantity, 473.18)
        self.assertEqual(result[0].unit, "mL")

    def test_ounces_to_grams(self):
        ingredients = [Ingredient("Cheese", 4, "oz")]

        result = convert_to_metric(ingredients)

        self.assertEqual(result[0].quantity, 113.4)
        self.assertEqual(result[0].unit, "g")

    def test_fluid_ounces_to_milliliters(self):
        ingredients = [Ingredient("Water", 2, "fl oz")]

        result = convert_to_metric(ingredients)

        self.assertEqual(result[0].quantity, 59.15)
        self.assertEqual(result[0].unit, "mL")

    def test_unsupported_units_remain_unchanged(self):
        ingredients = [Ingredient("Garlic", 3, "cloves")]

        result = convert_to_metric(ingredients)

        self.assertEqual(result[0], ingredients[0])

    def test_original_ingredients_not_modified(self):
        ingredients = [Ingredient("Milk", 2, "cups")]

        convert_to_metric(ingredients)

        self.assertEqual(ingredients[0].quantity, 2)
        self.assertEqual(ingredients[0].unit, "cups")

    def test_case_insensitive_conversion(self):
        ingredients = [Ingredient("Milk", 1, "CUPS")]

        result = convert_to_metric(ingredients)

        self.assertEqual(result[0].quantity, 236.59)
        self.assertEqual(result[0].unit, "mL")

    def test_serving_scaling_and_conversion(self):
        recipe = Recipe(
            id="test-20",
            title="Milk Recipe",
            ingredients=[Ingredient("Milk", 1, "cup")],
            steps=["Mix"],
            servings=2,
        )

        service = RecipeService([recipe])

        scaled = service.scale_ingredients("test-20", 4)
        converted = convert_to_metric(scaled)

        self.assertEqual(converted[0].quantity, 473.18)
        self.assertEqual(converted[0].unit, "mL")

        # The original saved recipe must remain unchanged.
        self.assertEqual(service.get("test-20").ingredients[0].quantity, 1)
        self.assertEqual(service.get("test-20").ingredients[0].unit, "cup")

    def test_multiple_ingredients(self):
        ingredients = [
            Ingredient("Milk", 2, "cups"),
            Ingredient("Cheese", 4, "oz"),
            Ingredient("Garlic", 3, "cloves"),
        ]

        result = convert_to_metric(ingredients)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].unit, "mL")
        self.assertEqual(result[1].unit, "g")
        self.assertEqual(result[2].unit, "cloves")


class MeasurementRouteTests(unittest.TestCase):

    def setUp(self):
        from app import create_app
        from app.services.users import UserService

        self.recipe = Recipe(
            id="metric-test",
            title="Metric Test Recipe",
            ingredients=[
                Ingredient("Milk", 2, "cups"),
                Ingredient("Cheese", 4, "oz"),
                Ingredient("Garlic", 3, "cloves"),
            ],
            steps=["Mix ingredients"],
            servings=2,
        )

        self.service = RecipeService([self.recipe])
        self.app = create_app(self.service, UserService())
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        self.client.post(
            "/register",
            data={
                "name": "Metric Tester",
                "email": "metric@example.com",
                "password": "Password123!",
                "password_confirm": "Password123!",
            },
        )

    def test_metric_conversion_on_recipe_page(self):
        response = self.client.get("/recipes/metric-test?units=metric")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("473.18 mL Milk", html)
        self.assertIn("113.4 g Cheese", html)
        self.assertIn("3 cloves Garlic", html)

    def test_original_measurements_remain_available(self):
        response = self.client.get("/recipes/metric-test?units=original")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("2 cups Milk", html)
        self.assertIn("4 oz Cheese", html)

    def test_scaling_and_conversion_together(self):
        response = self.client.get(
            "/recipes/metric-test?servings=4&units=metric"
        )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("946.35 mL Milk", html)
        self.assertIn("226.8 g Cheese", html)
        self.assertIn("6 cloves Garlic", html)

    def test_invalid_servings_resets_metric_selection(self):
        response = self.client.get(
            "/recipes/metric-test?servings=abc&units=metric"
        )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Servings must be a whole number of at least 1",
            html,
        )

        self.assertIn("2 cups Milk", html)
        self.assertIn("4 oz Cheese", html)
        self.assertNotIn("473.18 mL Milk", html)

        self.assertRegex(
            html,
            r'<option value="original"\s+selected',
        )
        self.assertNotRegex(
            html,
            r'<option value="metric"\s+selected',
        )

if __name__ == "__main__":
    unittest.main()