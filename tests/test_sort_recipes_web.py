
import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class SortRecipesWebTests(unittest.TestCase):

    def setUp(self):
        self.service = RecipeService([
            Recipe("b", "Banana Bread", [], ["Bake"]),
            Recipe("a", "Apple Pie", [], ["Bake"]),
            Recipe("c", "Carrot Soup", [], ["Cook"]),
        ])
        self.client = sign_in(
            create_app(self.service).test_client()
        )

    def check_order(self, url, expected_ids):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        positions = [
            html.index(f'href="/recipes/{recipe_id}"')
            for recipe_id in expected_ids
        ]
        self.assertEqual(positions, sorted(positions))

    def test_sort_az(self):
        self.check_order("/?sort=az", ["a", "b", "c"])

    def test_sort_za(self):
        self.check_order("/?sort=za", ["c", "b", "a"])

    def test_sort_newest_first(self):
        self.check_order("/?sort=newest", ["c", "a", "b"])

    def test_sort_with_search(self):
        self.check_order(
            "/?q=a&sort=az", ["a", "b", "c"]
        )

    def test_sort_does_not_change_saved_recipes(self):
        self.client.get("/?sort=az")
        self.assertEqual(
            [r.id for r in self.service.list_recipes()],
            ["b", "a", "c"]
        )


if __name__ == "__main__":
    unittest.main()
