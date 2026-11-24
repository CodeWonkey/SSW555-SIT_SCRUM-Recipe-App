"""US-42: saved leftover portions and dates survive page reloads."""
import unittest
from datetime import date

from app import create_app
from app.services.recipes import Recipe, RecipeService
from app.services.users import UserService
from tests.tests_helpers import sign_in


class LeftoversTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([Recipe("pasta", "Pasta", [], ["Cook"]),
                                      Recipe("soup", "Soup", [], ["Boil"])])
        self.users = UserService()
        self.alice = self.users.register(name="Alice", email="alice@example.com", password="password123")
        self.bob = self.users.register(name="Bob", email="bob@example.com", password="password123")
        self.app = create_app(self.service, self.users)
        self.client = sign_in(self.app.test_client(), self.alice.id, self.alice.name)

    def save(self, portions="2", stored_on="2026-11-24", recipe_id="pasta"):
        return self.client.post(f"/recipes/{recipe_id}/leftovers",
                                data={"portions": portions, "stored_on": stored_on})

    def test_recipe_form_and_navigation(self):
        html = self.client.get("/recipes/pasta").get_data(as_text=True)
        self.assertIn('name="portions"', html)
        self.assertIn('name="stored_on"', html)
        self.assertIn("/recipes/pasta/leftovers", html)
        self.assertIn('href="/leftovers"', html)

    def test_save_and_page_reload(self):
        self.assertEqual(self.save().status_code, 302)
        for _ in range(2):  # Reloading must show the same saved record.
            response = self.client.get("/leftovers")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Pasta", response.data)
            self.assertIn(b"2 portions", response.data)
            self.assertIn(b"November 24, 2026", response.data)

    def test_entries_ordered_newest_first(self):
        self.save("1", "2026-11-01", "pasta")
        self.save("3", "2026-11-20", "soup")
        page = self.client.get("/leftovers").get_data(as_text=True)
        self.assertLess(page.index("Soup"), page.index("Pasta"))

    def test_account_isolation(self):
        self.save()
        other = sign_in(self.app.test_client(), self.bob.id, self.bob.name)
        page = other.get("/leftovers").data
        self.assertNotIn(b"2 portions", page)
        self.assertIn(b"haven't saved any leftovers", page)

    def test_invalid_portions_and_dates_rejected(self):
        for quantity, day in [("0", "2026-11-24"), ("-3", "2026-11-24"),
                              ("abc", "2026-11-24"), ("1.5", "2026-11-24"),
                              ("2", "not-a-date"), ("2", "")]:
            with self.subTest(quantity=quantity, day=day):
                self.assertEqual(self.save(quantity, day).status_code, 302)
        self.assertEqual(self.users.get_leftovers(self.alice.id), [])

    def test_unknown_recipe_returns_404(self):
        self.assertEqual(self.save(recipe_id="missing").status_code, 404)

    def test_unauthenticated_access_redirects(self):
        guest = self.app.test_client()
        self.assertEqual(guest.get("/leftovers").status_code, 302)
        self.assertEqual(guest.post("/recipes/pasta/leftovers").status_code, 302)

    def test_deleted_recipe_does_not_break_page(self):
        self.save()
        self.service.delete("pasta")
        response = self.client.get("/leftovers")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"haven't saved any leftovers", response.data)

    def test_service_validates_data(self):
        with self.assertRaises(ValueError):
            self.users.save_leftovers(self.alice.id, "pasta", 0, date(2026, 11, 24))
        with self.assertRaises(ValueError):
            self.users.save_leftovers(self.alice.id, "pasta", True, date(2026, 11, 24))
        with self.assertRaises(ValueError):
            self.users.save_leftovers(self.alice.id, "pasta", 1, "2026-11-24")
        self.assertEqual(len(self.alice.leftovers), 0)

if __name__ == "__main__":
    unittest.main()
