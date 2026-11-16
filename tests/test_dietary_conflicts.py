"""US-21: Mark recipes that conflict with saved dietary preferences.

A recipe is "May not be suitable" when the signed-in user has a saved
restriction or allergy and the recipe is missing the matching label.
Vegan satisfies vegetarian. No saved preferences, and signed-out visitors,
leave every recipe unmarked. A custom allergy expects an "{allergy}-free" label.
"""

import re
import unittest

from app import create_app
from app.services.diet_labels import is_unsuitable
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService

from tests.tests_helpers import sign_in


WARNING = "May not be suitable"

# Profile value -> label that satisfies it.
DIET_LABELS = (
    ("vegetarian", "vegetarian"),
    ("vegan", "vegan"),
    ("gluten-free", "gluten-free"),
    ("dairy-free", "dairy-free"),
)
ALLERGEN_LABELS = (
    ("peanuts", "peanut-free"),
    ("tree-nuts", "tree-nut-free"),
    ("shellfish", "shellfish-free"),
    ("eggs", "egg-free"),
    ("soy", "soy-free"),
    ("sesame", "sesame-free"),
)


def make_recipe(recipe_id="soup", title="Soup", labels=()):
    return Recipe(
        recipe_id,
        title,
        [Ingredient("Carrot", 1)],
        ["Simmer"],
        diet_labels=set(labels),
    )


def checked_diet_labels(html):
    values = set()
    for tag in re.findall(r"<input\b[^>]*>", html):
        if 'name="diet_labels"' not in tag or "checked" not in tag:
            continue
        found = re.search(r'value="([^"]*)"', tag)
        if found:
            values.add(found.group(1))
    return values


_next_user = 0


def make_user(users, *, restrictions=(), allergies=(), other=""):
    global _next_user
    _next_user += 1
    email = f"ada{_next_user}@example.com"
    user = users.register(
        name="Ada",
        email=email,
        password="password-123",
    )
    users.update_profile_preferences(user.id, restrictions, allergies, other)
    return users.get(user.id)


class DietConflictRuleTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()

    def test_no_saved_preferences_leaves_an_unlabeled_recipe_unmarked(self):
        user = make_user(self.users)
        self.assertFalse(is_unsuitable(make_recipe(), user))

    def test_signed_out_visitor_leaves_an_unlabeled_recipe_unmarked(self):
        self.assertFalse(is_unsuitable(make_recipe(), None))

    def test_each_diet_needs_its_own_label(self):
        for restriction, label in DIET_LABELS:
            with self.subTest(restriction=restriction):
                user = make_user(self.users, restrictions=[restriction])
                self.assertTrue(is_unsuitable(make_recipe(), user))
                self.assertFalse(is_unsuitable(make_recipe(labels=[label]), user))

    def test_each_allergy_needs_its_free_label(self):
        for allergy, label in ALLERGEN_LABELS:
            with self.subTest(allergy=allergy):
                user = make_user(self.users, allergies=[allergy])
                self.assertTrue(is_unsuitable(make_recipe(), user))
                self.assertFalse(is_unsuitable(make_recipe(labels=[label]), user))

    def test_vegan_label_satisfies_a_vegetarian_restriction(self):
        user = make_user(self.users, restrictions=["vegetarian"])
        self.assertFalse(is_unsuitable(make_recipe(labels=["vegan"]), user))
        self.assertFalse(is_unsuitable(make_recipe(labels=["Vegan"]), user))

    def test_vegetarian_label_does_not_satisfy_a_vegan_restriction(self):
        user = make_user(self.users, restrictions=["vegan"])
        self.assertTrue(is_unsuitable(make_recipe(labels=["vegetarian"]), user))

    def test_vegan_label_does_not_satisfy_other_diets(self):
        user = make_user(self.users, restrictions=["dairy-free", "gluten-free"])
        self.assertTrue(is_unsuitable(make_recipe(labels=["vegan"]), user))

    def test_one_missing_label_marks_the_recipe_when_another_matches(self):
        user = make_user(
            self.users,
            restrictions=["vegetarian"],
            allergies=["peanuts"],
        )
        self.assertTrue(is_unsuitable(make_recipe(labels=["vegan"]), user))
        self.assertFalse(
            is_unsuitable(make_recipe(labels=["vegan", "peanut-free"]), user)
        )

    def test_custom_allergy_needs_a_matching_free_label(self):
        user = make_user(self.users, other="Kiwi")
        self.assertTrue(is_unsuitable(make_recipe(), user))
        self.assertFalse(is_unsuitable(make_recipe(labels=["kiwi-free"]), user))
        self.assertFalse(is_unsuitable(make_recipe(labels=["Kiwi-free"]), user))

    def test_custom_allergy_match_ignores_case_and_extra_space(self):
        user = make_user(self.users, other="  KIWI ")
        self.assertFalse(is_unsuitable(make_recipe(labels=["kiwi-free"]), user))


class DietConflictPageTests(unittest.TestCase):
    def setUp(self):
        self.unlabeled = make_recipe("plain", "Tomato Pasta")
        self.vegan = make_recipe("vegan", "Vegan Soup", ["vegan"])
        self.recipes = RecipeService([self.unlabeled, self.vegan])
        self.users = UserService()
        self.app = create_app(self.recipes, self.users)

    def client_for(self, user):
        client = self.app.test_client()
        if user is not None:
            sign_in(client, user.id, user.name)
        return client

    def card(self, html, title):
        for piece in html.split("<article")[1:]:
            if title in piece:
                return piece
        self.fail(f"{title} was not on the page")

    def test_signed_out_visitor_is_sent_to_login(self):
        client = self.client_for(None)
        for path in ("/", "/recipes/plain", "/recipes/vegan"):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.headers["Location"])
                self.assertNotIn(WARNING, response.get_data(as_text=True))

    def test_user_with_no_preferences_sees_no_warning(self):
        client = self.client_for(make_user(self.users))
        page = client.get("/").get_data(as_text=True)
        detail = client.get("/recipes/plain").get_data(as_text=True)
        self.assertNotIn(WARNING, page)
        self.assertNotIn(WARNING, detail)

    def test_missing_label_is_marked_on_the_list_and_the_detail_page(self):
        client = self.client_for(make_user(self.users, restrictions=["vegetarian"]))
        page = client.get("/").get_data(as_text=True)
        detail = client.get("/recipes/plain").get_data(as_text=True)

        self.assertIn(WARNING, self.card(page, "Tomato Pasta"))
        self.assertNotIn(WARNING, self.card(page, "Vegan Soup"))
        self.assertIn("Tomato Pasta", detail)
        self.assertIn(WARNING, detail)

    def test_vegan_recipe_is_unmarked_for_a_vegetarian(self):
        client = self.client_for(make_user(self.users, restrictions=["vegetarian"]))
        detail = client.get("/recipes/vegan").get_data(as_text=True)
        self.assertIn("Vegan Soup", detail)
        self.assertNotIn(WARNING, detail)

    def test_warning_follows_the_viewer(self):
        vegetarian = make_user(self.users, restrictions=["vegetarian"])
        other = self.users.register(
            name="Bea",
            email="bea@example.com",
            password="password-456",
        )
        restricted = self.client_for(vegetarian).get("/recipes/plain").get_data(as_text=True)
        unrestricted = self.client_for(other).get("/recipes/plain").get_data(as_text=True)
        self.assertIn(WARNING, restricted)
        self.assertNotIn(WARNING, unrestricted)

    def test_custom_allergy_marks_until_its_label_is_checked(self):
        user = make_user(self.users, other="Kiwi")
        client = self.client_for(user)
        missing = client.get("/recipes/plain").get_data(as_text=True)
        self.assertIn(WARNING, missing)

        self.vegan.diet_labels.add("kiwi-free")
        checked = client.get("/recipes/vegan").get_data(as_text=True)
        self.assertIn("Vegan Soup", checked)
        self.assertNotIn(WARNING, checked)


class DietLabelFormTests(unittest.TestCase):
    def setUp(self):
        self.recipes = RecipeService()
        self.users = UserService()
        self.user = make_user(self.users, other="Kiwi")
        self.app = create_app(self.recipes, self.users)
        self.client = sign_in(self.app.test_client(), self.user.id, self.user.name)

    def form(self, **overrides):
        data = {
            "title": "Pancakes",
            "servings": "4",
            "ingredient_name[]": ["Flour"],
            "ingredient_quantity[]": ["2"],
            "ingredient_unit[]": ["cups"],
            "steps": "Cook",
            "diet_labels": ["vegan", "kiwi-free"],
        }
        data.update(overrides)
        return data

    def test_add_form_lists_standard_labels_and_the_custom_allergy(self):
        html = self.client.get("/recipes/add").get_data(as_text=True)
        for label in (
            "Vegetarian",
            "Vegan",
            "Gluten-free",
            "Dairy-free",
            "Peanut-free",
            "Tree-nut-free",
            "Shellfish-free",
            "Egg-free",
            "Soy-free",
            "Sesame-free",
            "Kiwi-free",
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)
        self.assertIn('value="kiwi-free"', html)
        self.assertIn('name="diet_labels"', html)

    def test_checking_labels_saves_them_on_the_recipe(self):
        self.client.post("/recipes/add", data=self.form())
        saved = self.recipes.list_recipes()[0]
        self.assertEqual(saved.diet_labels, {"vegan", "kiwi-free"})
        self.assertFalse(is_unsuitable(saved, self.user))

    def test_edit_form_keeps_a_custom_label_the_editor_does_not_have(self):
        recipe = make_recipe("pancakes", "Pancakes", ["vegan", "mustard-free"])
        self.recipes.create(recipe)
        html = self.client.get("/recipes/pancakes/edit").get_data(as_text=True)
        self.assertIn("mustard-free", html)
        self.assertIn("Kiwi-free", html)
        self.assertEqual(checked_diet_labels(html), {"vegan", "mustard-free"})
