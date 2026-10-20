import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService


class SearchWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe("pasta", "Tomato Pasta", [Ingredient("Olive oil", 1, "tbsp")], ["Cook"]),
            Recipe("soup", "Vegetable Soup", [Ingredient("Tomatoes", 2, "cups")], ["Simmer"]),
            Recipe("salad", "Green Salad", [Ingredient("Lettuce", 1)], ["Mix"]),
        ])
        self.client = create_app(self.service).test_client()

    def test_home_has_search_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'role="search"', response.data)
        self.assertIn(b'method="GET"', response.data)
        self.assertIn(b'<label for="recipe-search">', response.data)
        self.assertIn(b'name="q"', response.data)

    def test_search_matches_name_and_ingredient_ignoring_case(self):
        for query, expected_ids in (
            ("pasta", ["pasta"]),
            ("PASTA", ["pasta"]),
            ("olive", ["pasta"]),
            ("OLIVE", ["pasta"]),
            ("ToMaTo", ["pasta", "soup"]),
            ("  soup  ", ["soup"]),
        ):
            with self.subTest(query=query):
                response = self.client.get("/", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                for recipe in self.service.list_recipes():
                    link = f'href="/recipes/{recipe.id}"'.encode()
                    if recipe.id in expected_ids:
                        self.assertIn(link, response.data)
                    else:
                        self.assertNotIn(link, response.data)
                self.assertIn(f'value="{query.strip()}"'.encode(), response.data)

    def test_no_matches_shows_search_empty_state(self):
        response = self.client.get("/", query_string={"q": "chocolate"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recipes found.", response.data)
        self.assertIn(b"Try another recipe name or ingredient.", response.data)
        self.assertNotIn(b'class="recipe-card"', response.data)
        self.assertNotIn(b"Your recipe box is ready", response.data)

    def test_search_displays_result_count_and_clear_link(self):
        for query, count in (("pasta", "1 recipe found"), ("tomato", "2 recipes found"),
                             ("chocolate", "0 recipes found")):
            with self.subTest(query=query):
                response = self.client.get("/", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertIn(count.encode(), response.data)
                self.assertIn(b'href="/">Clear search</a>', response.data)

    def test_blank_query_and_cleared_search_show_all_recipes(self):
        self.client.get("/", query_string={"q": "pasta"})
        for query_string in ({}, {"q": ""}, {"q": "   "}):
            with self.subTest(query_string=query_string):
                response = self.client.get("/", query_string=query_string)
                self.assertEqual(response.status_code, 200)
                for recipe in self.service.list_recipes():
                    self.assertIn(f'href="/recipes/{recipe.id}"'.encode(), response.data)
                self.assertNotIn(b"Clear search", response.data)

    def test_search_on_empty_collection(self):
        response = create_app(RecipeService()).test_client().get("/?q=pasta")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recipes found.", response.data)

    def test_search_query_is_escaped(self):
        response = self.client.get("/", query_string={"q": '<script>alert("x")</script>'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)

    def test_newly_saved_recipe_is_searchable(self):
        self.client.post("/recipes/add", data={
            "title": "Pancakes",
            "ingredient_name[]": ["Flour"],
            "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["cups"],
            "steps": "Mix and cook",
        })
        for query in ("PANCAKES", "FLOUR"):
            with self.subTest(query=query):
                response = self.client.get("/", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Pancakes", response.data)
                self.assertNotIn(b"Tomato Pasta", response.data)


if __name__ == "__main__":
    unittest.main()
