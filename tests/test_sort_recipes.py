"""US-09: sorting the collection and search results without changing saved data."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService, SORT_OPTIONS
from tests.tests_helpers import sign_in


def sample_service():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Input order differs from both title order and creation order.
    return RecipeService([
        Recipe("z", "zucchini Soup", [], ["Cook"], created_at=start),
        Recipe("a", "apple Soup", [], ["Simmer"], created_at=start + timedelta(days=2)),
        Recipe("b", "Banana Bread", [], ["Bake"], created_at=start + timedelta(days=1)),
    ])


class PageParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.recipe_links = []
        self.clear_link = None
        self.selected = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            href = attrs.get("href", "")
            if href.startswith("/recipes/") and href != "/recipes/add":
                self.recipe_links.append(href)
            if href.startswith("/?sort="):
                self.clear_link = href
        if tag == "option" and "selected" in attrs:
            self.selected.append(attrs["value"])


class SortRecipesServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()

    def test_all_sort_orders(self):
        for sort, ids in (
            ("alphabetical", ["a", "b", "z"]),
            ("alphabetical_desc", ["z", "b", "a"]),
            ("newest", ["a", "b", "z"]),
            ("oldest", ["z", "b", "a"]),
        ):
            with self.subTest(sort=sort):
                self.assertEqual([r.id for r in self.service.list_recipes(sort=sort)], ids)

    def test_sort_does_not_mutate_recipes_or_original_collection_order(self):
        before = deepcopy(self.service.list_recipes())
        for sort in SORT_OPTIONS:
            result = self.service.list_recipes(sort=sort)
            result.clear()
            self.assertEqual(self.service.list_recipes(), before)

    def test_equal_keys_keep_input_order(self):
        first = self.service.get("a")
        self.service.create(Recipe("a2", "APPLE SOUP", [], [], created_at=first.created_at))
        for sort in SORT_OPTIONS:
            ids = [r.id for r in self.service.list_recipes(sort=sort)]
            self.assertLess(ids.index("a"), ids.index("a2"))

    def test_invalid_sort_is_rejected_even_for_empty_results(self):
        for query in ("", "missing"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.service.search(query, sort="unsupported")

    def test_empty_and_single_recipe_collections(self):
        service = RecipeService()
        for sort in SORT_OPTIONS:
            self.assertEqual(service.list_recipes(sort=sort), [])
        recipe = service.create(Recipe("only", "Only Recipe", [], []))
        for sort in SORT_OPTIONS:
            self.assertEqual(service.list_recipes(sort=sort), [recipe])

    def test_new_recipes_get_utc_timestamp_and_editing_preserves_it(self):
        before = datetime.now(timezone.utc)
        recipe = self.service.create(Recipe("new", "New Recipe", [], []))
        self.assertLessEqual(before, recipe.created_at)
        self.assertLessEqual(recipe.created_at, datetime.now(timezone.utc))
        created_at = recipe.created_at
        self.service.update("new", title="Updated")
        self.assertEqual(recipe.created_at, created_at)
        self.assertEqual(self.service.list_recipes(sort="newest")[0].id, "new")

    def test_naive_imported_date_is_treated_as_utc(self):
        self.service.get("a").created_at = datetime(2026, 1, 3)
        self.assertEqual([r.id for r in self.service.list_recipes(sort="newest")],
                         ["a", "b", "z"])


class SortRecipesWebTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()
        self.client = sign_in(create_app(self.service).test_client())

    def page(self, params=None):
        response = self.client.get("/", query_string=params or {})
        self.assertEqual(response.status_code, 200)
        return response, PageParser(response.get_data(as_text=True))

    def test_sort_form_and_rendered_orders(self):
        for sort, ids in (
            ("alphabetical", ["a", "b", "z"]),
            ("alphabetical_desc", ["z", "b", "a"]),
            ("newest", ["a", "b", "z"]),
            ("oldest", ["z", "b", "a"]),
        ):
            with self.subTest(sort=sort):
                response, page = self.page({"sort": sort})
                self.assertEqual(page.recipe_links, [f"/recipes/{id}" for id in ids])
                self.assertEqual(page.selected, [sort])
                self.assertIn(b'<label for="recipe-sort">', response.data)
                self.assertIn(b'<select id="recipe-sort" name="sort">', response.data)
                self.assertIn(b'type="submit"', response.data)

    def test_default_and_invalid_sort_fall_back_to_newest(self):
        for params in ({}, {"sort": ""}, {"sort": "unsupported"}):
            with self.subTest(params=params):
                _, page = self.page(params)
                self.assertEqual(page.recipe_links, ["/recipes/a", "/recipes/b", "/recipes/z"])
                self.assertEqual(page.selected, ["newest"])

    def test_sort_combines_with_search_and_survives_clear_and_reload(self):
        for sort, ids in (("alphabetical", ["a", "z"]), ("oldest", ["z", "a"])):
            with self.subTest(sort=sort):
                for _ in range(2):
                    response, page = self.page({"q": "Soup", "sort": sort})
                    self.assertEqual(page.recipe_links, [f"/recipes/{id}" for id in ids])
                    self.assertIn(b'value="Soup"', response.data)
                    self.assertIn(b"2 recipes found", response.data)
                    self.assertEqual(page.selected, [sort])
                cleared = self.client.get(page.clear_link)
                self.assertEqual(PageParser(cleared.get_data(as_text=True)).selected, [sort])
                self.assertEqual(len(PageParser(cleared.get_data(as_text=True)).recipe_links), 3)

    def test_empty_results_keep_sort_control(self):
        response, page = self.page({"q": "missing", "sort": "alphabetical"})
        self.assertIn(b"No recipes found.", response.data)
        self.assertEqual(page.recipe_links, [])
        self.assertEqual(page.selected, ["alphabetical"])

    def test_recipe_added_through_form_appears_first_in_newest_order(self):
        response = self.client.post("/recipes/add", data={"title": "New Soup", "steps": "Cook"})
        self.assertEqual(response.status_code, 302)
        added = next(r for r in self.service.list_recipes() if r.title == "New Soup")
        _, page = self.page({"sort": "newest"})
        self.assertEqual(page.recipe_links[0], f"/recipes/{added.id}")


if __name__ == "__main__":
    unittest.main()
