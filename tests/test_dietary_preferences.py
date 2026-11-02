"""US-15: Set dietary restrictions.

Acceptance criteria covered:
- a signed-in user can open profile settings
- selecting restrictions such as vegetarian, gluten-free, and dairy-free saves them
- saved preferences are stored on the account and displayed on the profile
- reopening the profile shows the saved choices, and saving again replaces them
"""

import unittest

from app import create_app
from app.services.recipes import RecipeService
from app.services.users import DIETARY_RESTRICTIONS, UserService


def register_user(users, *, name="John Doe", email="john@example.com", password="johnnydoe-123"):
    return users.register(name=name, email=email, password=password)


class DietaryPreferenceServiceTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()
        self.user = register_user(self.users)

    def test_new_account_has_no_dietary_restrictions(self):
        self.assertEqual(self.user.dietary_restrictions, set())
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, set())

    def test_save_multiple_restrictions(self):
        updated = self.users.update_dietary_restrictions(
            self.user.id,
            ["vegetarian", "gluten-free", "dairy-free"],
        )

        self.assertEqual(
            updated.dietary_restrictions,
            {"vegetarian", "gluten-free", "dairy-free"},
        )
        reopened = self.users.get(self.user.id)
        self.assertEqual(reopened.dietary_restrictions, updated.dietary_restrictions)

    def test_save_normalizes_case_whitespace_and_duplicates(self):
        updated = self.users.update_dietary_restrictions(
            self.user.id,
            ["  Vegetarian ", "GLUTEN-FREE", "gluten-free"],
        )

        self.assertEqual(updated.dietary_restrictions, {"vegetarian", "gluten-free"})

    def test_editing_replaces_the_saved_set(self):
        self.users.update_dietary_restrictions(self.user.id, ["vegetarian", "gluten-free"])
        updated = self.users.update_dietary_restrictions(self.user.id, ["dairy-free"])

        self.assertEqual(updated.dietary_restrictions, {"dairy-free"})
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, {"dairy-free"})

    def test_saving_nothing_clears_saved_restrictions(self):
        self.users.update_dietary_restrictions(self.user.id, ["vegetarian"])
        updated = self.users.update_dietary_restrictions(self.user.id, [])

        self.assertEqual(updated.dietary_restrictions, set())

    def test_unknown_restriction_is_rejected_without_changing_saved_values(self):
        self.users.update_dietary_restrictions(self.user.id, ["vegetarian"])

        with self.assertRaises(ValueError):
            self.users.update_dietary_restrictions(self.user.id, ["vegetarian", "keto"])

        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, {"vegetarian"})

    def test_missing_account_cannot_be_updated(self):
        with self.assertRaises(ValueError):
            self.users.update_dietary_restrictions("missing", ["vegetarian"])

    def test_preferences_are_stored_separately_per_account(self):
        other = register_user(self.users, name="Alex Smith", email="alex@example.com")
        self.users.update_dietary_restrictions(self.user.id, ["vegetarian"])
        self.users.update_dietary_restrictions(other.id, ["dairy-free"])

        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, {"vegetarian"})
        self.assertEqual(self.users.get(other.id).dietary_restrictions, {"dairy-free"})

    def test_allowed_choices_match_the_profile_options(self):
        self.assertEqual(
            [value for value, _label in DIETARY_RESTRICTIONS],
            ["vegetarian", "gluten-free", "dairy-free"],
        )


class ProfileDietaryWebTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()
        self.user = register_user(self.users)
        self.client = create_app(RecipeService(), self.users).test_client()

    def login(self, email="john@example.com", password="johnnydoe-123"):
        return self.client.post("/login", data={"email": email, "password": password})

    def saved_preferences(self, html: str) -> str:
        start = html.split('id="saved-preferences"', 1)[1]
        return start.split("</ul>", 1)[0]

    def test_profile_requires_login(self):
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        response = self.client.post("/profile", data={"dietary_restrictions": "vegetarian"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, set())

    def test_profile_settings_list_dietary_choices(self):
        self.login()
        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"John Doe", response.data)
        self.assertIn(b"Dietary restrictions", response.data)
        for value, label in DIETARY_RESTRICTIONS:
            self.assertIn(f'value="{value}"'.encode(), response.data)
            self.assertIn(label.encode(), response.data)
        self.assertIn(b"No dietary restrictions saved.", response.data)

    def test_saving_restrictions_stores_and_displays_them(self):
        self.login()
        response = self.client.post(
            "/profile",
            data={"dietary_restrictions": ["vegetarian", "gluten-free"]},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        html = response.data.decode()
        saved = self.saved_preferences(html)
        self.assertIn("Vegetarian", saved)
        self.assertIn("Gluten-free", saved)
        self.assertNotIn("Dairy-free", saved)
        self.assertIn('value="vegetarian" checked', html)
        self.assertIn('value="gluten-free" checked', html)
        self.assertNotIn('value="dairy-free" checked', html)
        self.assertEqual(
            self.users.get(self.user.id).dietary_restrictions,
            {"vegetarian", "gluten-free"},
        )

    def test_reopening_profile_shows_saved_preferences(self):
        self.login()
        self.client.post("/profile", data={"dietary_restrictions": ["dairy-free"]})

        response = self.client.get("/profile")
        html = response.data.decode()
        saved = self.saved_preferences(html)
        self.assertIn("Dairy-free", saved)
        self.assertIn('value="dairy-free" checked', html)
        self.assertNotIn('value="vegetarian" checked', html)

    def test_editing_preferences_replaces_what_is_displayed(self):
        self.login()
        self.client.post(
            "/profile",
            data={"dietary_restrictions": ["vegetarian", "gluten-free"]},
        )

        response = self.client.post(
            "/profile",
            data={"dietary_restrictions": "dairy-free"},
            follow_redirects=True,
        )
        html = response.data.decode()
        saved = self.saved_preferences(html)
        self.assertIn("Dairy-free", saved)
        self.assertNotIn("Vegetarian", saved)
        self.assertNotIn("Gluten-free", saved)
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, {"dairy-free"})

    def test_clearing_all_choices_removes_saved_preferences(self):
        self.login()
        self.client.post("/profile", data={"dietary_restrictions": "vegetarian"})

        response = self.client.post("/profile", data={}, follow_redirects=True)
        self.assertIn(b"No dietary restrictions saved.", response.data)
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, set())

    def test_unknown_restriction_is_not_saved(self):
        self.login()
        self.client.post("/profile", data={"dietary_restrictions": "vegetarian"})

        response = self.client.post(
            "/profile",
            data={"dietary_restrictions": ["vegetarian", "keto"]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Unsupported dietary restriction", response.data)
        self.assertEqual(self.users.get(self.user.id).dietary_restrictions, {"vegetarian"})

    def test_signed_in_navigation_links_to_profile(self):
        self.login()
        response = self.client.get("/", follow_redirects=True)
        self.assertIn(b'href="/profile"', response.data)


if __name__ == "__main__":
    unittest.main()
