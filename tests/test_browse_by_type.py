"""US-05 regression tests for recipe-type search and combined filters."""

import unittest

from app import create_app
from app.services.recipes import Ingredient, Recipe, RecipeService


def sample_service():
    # Type names appear only in tags, so title/ingredient/step matches cannot
    # accidentally make the tag-search tests pass.
    return RecipeService([
        Recipe("oats", "Rolled Oats", [Ingredient("Oats", 1, "cup")],
               ["Stir and cook"], tags={"Breakfast", "Quick"}, favorite=True),
        Recipe("toast", "Avocado Toast", [Ingredient("Avocado", 1)],
               ["Spread and serve"], tags={"bReAkFaSt"}),
        Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2)],
               ["Boil and serve"], tags={"Dinner"}, favorite=True),
        Recipe("soup", "Vegetable Soup", [Ingredient("Carrot", 1)],
               ["Simmer and serve"], tags={"Lunch"}),
    ])


class BrowseByTypeServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()

    def test_search_finds_type_stored_only_in_tags(self):
        self.assertEqual(
            [recipe.id for recipe in self.service.search("Breakfast")],
            ["oats", "toast"],
        )

    def test_type_search_ignores_case_and_surrounding_whitespace(self):
        for query in ("BREAKFAST", "  breakfast  ", "BrEaKfAsT"):
            with self.subTest(query=query):
                self.assertEqual(
                    [recipe.id for recipe in self.service.search(query)],
                    ["oats", "toast"],
                )

    def test_unknown_type_returns_no_matches(self):
        self.assertEqual(self.service.search("Dessert"), [])

    def test_category_filter_excludes_other_types(self):
        self.assertEqual(
            [recipe.id for recipe in self.service.filter(tag="BREAKFAST")],
            ["oats", "toast"],
        )

    def test_combined_category_and_favorites_filters_require_both(self):
        # Toast matches only the type, pasta only favorites, and soup neither.
        self.assertEqual(
            [recipe.id for recipe in self.service.filter(
                tag="Breakfast", favorites_only=True
            )],
            ["oats"],
        )
        self.assertEqual(
            self.service.filter(tag="Lunch", favorites_only=True), []
        )


class BrowseByTypeWebTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()
        self.client = create_app(self.service).test_client()

    def test_searching_by_type_displays_only_matching_recipe_links(self):
        for query in ("Breakfast", "BREAKFAST", "  breakfast  "):
            with self.subTest(query=query):
                response = self.client.get("/", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                for recipe_id in ("oats", "toast"):
                    self.assertIn(
                        f'href="/recipes/{recipe_id}"'.encode(), response.data
                    )
                for recipe_id in ("pasta", "soup"):
                    self.assertNotIn(
                        f'href="/recipes/{recipe_id}"'.encode(), response.data
                    )
                self.assertIn(b"2 recipes found", response.data)

    def test_unknown_type_displays_no_results(self):
        response = self.client.get("/", query_string={"q": "Dessert"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recipes found.", response.data)
        self.assertNotIn(b'class="recipe-card"', response.data)

    def test_new_recipe_is_searchable_by_its_type_tag(self):
        response = self.client.post("/recipes/add", data={
            "title": "Egg Plate",
            "servings": "1",
            "tags": "Brunch, Quick",
            "ingredient_name[]": ["Egg"],
            "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": [""],
            "steps": "Cook and serve",
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/", query_string={"q": "BRUNCH"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Egg Plate", response.data)
        self.assertIn(b"1 recipe found", response.data)
        for recipe_id in ("oats", "toast", "pasta", "soup"):
            self.assertNotIn(
                f'href="/recipes/{recipe_id}"'.encode(), response.data
            )


if __name__ == "__main__":
    unittest.main()
