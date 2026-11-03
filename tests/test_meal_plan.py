"""US-16: Create a weekly meal plan.

Acceptance criteria covered:
- the meal planner is a page linked from the main page
- the page shows every day of the week
- choosing a day and a saved recipe places that recipe on that day
- the plan belongs to the signed-in account and is still there after logging in again
"""

import unittest

from app import create_app
from app.services.meal_plan import add_recipe, empty_plan
from app.services.recipes import Ingredient, Recipe, RecipeService
from app.services.users import UserService


def sample_service():
    return RecipeService([
        Recipe("pasta", "Tomato Pasta", [Ingredient("Tomato", 2)], ["Boil"]),
        Recipe("soup", "Vegetable Soup", [Ingredient("Carrot", 1)], ["Simmer"]),
    ])


class MealPlanServiceTests(unittest.TestCase):
    def test_empty_plan_has_every_day(self):
        self.assertEqual(
            list(empty_plan()),
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        )
        self.assertTrue(all(recipes == [] for recipes in empty_plan().values()))

    def test_add_recipe_assigns_it_to_the_selected_day(self):
        plan = add_recipe(empty_plan(), "monday", "pasta")

        self.assertEqual(plan["monday"], ["pasta"])
        self.assertEqual(plan["tuesday"], [])

    def test_same_recipe_can_be_planned_on_more_than_one_day(self):
        plan = add_recipe(empty_plan(), "Monday", "pasta")
        plan = add_recipe(plan, "friday", "pasta")

        self.assertEqual(plan["monday"], ["pasta"])
        self.assertEqual(plan["friday"], ["pasta"])

    def test_adding_the_same_recipe_twice_does_not_duplicate_it(self):
        plan = add_recipe(empty_plan(), "monday", "pasta")
        plan = add_recipe(plan, "monday", "pasta")

        self.assertEqual(plan["monday"], ["pasta"])

    def test_unknown_day_is_rejected(self):
        with self.assertRaises(ValueError):
            add_recipe(empty_plan(), "yesterday", "pasta")

    def test_blank_recipe_is_rejected(self):
        with self.assertRaises(ValueError):
            add_recipe(empty_plan(), "monday", "  ")


class MealPlanWebTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()
        self.users = UserService()
        self.user = self.users.register(
            name="John Doe", email="john@example.com", password="johnnydoe-123"
        )
        self.client = create_app(self.service, self.users).test_client()

    def login(self, email="john@example.com", password="johnnydoe-123"):
        return self.client.post("/login", data={"email": email, "password": password})

    def day_section(self, html: str, day: str) -> str:
        start = html.split(f'id="day-{day}"', 1)[1]
        return start.split("</section>", 1)[0]

    def test_planner_requires_an_account(self):
        response = self.client.get("/meal-plan")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        response = self.client.post("/meal-plan", data={"day": "monday", "recipe_id": "pasta"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(self.users.get(self.user.id).meal_plan["monday"], [])

    def test_main_page_links_to_the_meal_planner(self):
        self.login()
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/meal-plan"', response.data)

    def test_planner_shows_the_whole_week(self):
        self.login()
        response = self.client.get("/meal-plan")
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weekly meal plan", response.data)
        self.assertIn(b'name="day"', response.data)
        self.assertIn(b'name="recipe_id"', response.data)
        self.assertIn(b"Tomato Pasta", response.data)
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            self.assertIn("Nothing planned.", self.day_section(html, day))

    def test_adding_a_saved_recipe_shows_it_on_that_day(self):
        self.login()
        response = self.client.post(
            "/meal-plan",
            data={"day": "monday", "recipe_id": "pasta"},
            follow_redirects=True,
        )
        html = response.data.decode()
        monday = self.day_section(html, "monday")
        tuesday = self.day_section(html, "tuesday")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tomato Pasta", monday)
        self.assertNotIn("Tomato Pasta", tuesday)
        self.assertIn("Nothing planned.", tuesday)
        self.assertEqual(self.users.get(self.user.id).meal_plan["monday"], ["pasta"])

    def test_plan_stays_with_the_account_after_logging_out(self):
        self.login()
        self.client.post("/meal-plan", data={"day": "wednesday", "recipe_id": "soup"})
        self.client.post("/logout")
        self.login()

        response = self.client.get("/meal-plan")
        wednesday = self.day_section(response.data.decode(), "wednesday")

        self.assertIn("Vegetable Soup", wednesday)
        self.assertEqual(self.users.get(self.user.id).meal_plan["wednesday"], ["soup"])

    def test_each_account_has_its_own_plan(self):
        self.login()
        self.client.post("/meal-plan", data={"day": "monday", "recipe_id": "pasta"})
        self.client.post("/logout")
        alex = self.users.register(name="Alex Smith", email="alex@example.com", password="alex-password-123")
        self.login("alex@example.com", "alex-password-123")

        response = self.client.get("/meal-plan")
        self.assertIn("Nothing planned.", self.day_section(response.data.decode(), "monday"))

        self.client.post("/meal-plan", data={"day": "monday", "recipe_id": "soup"})
        self.assertEqual(self.users.get(alex.id).meal_plan["monday"], ["soup"])
        self.assertEqual(self.users.get(self.user.id).meal_plan["monday"], ["pasta"])

    def test_missing_recipe_is_not_added(self):
        self.login()
        response = self.client.post("/meal-plan", data={"day": "monday", "recipe_id": "missing"})

        self.assertEqual(response.status_code, 404)
        follow = self.client.get("/meal-plan")
        self.assertIn("Nothing planned.", self.day_section(follow.data.decode(), "monday"))

    def test_unknown_day_is_rejected(self):
        self.login()
        response = self.client.post("/meal-plan", data={"day": "yesterday", "recipe_id": "pasta"})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Choose a day of the week", response.data)

    def test_removed_recipe_disappears_from_the_plan(self):
        self.login()
        self.client.post("/meal-plan", data={"day": "monday", "recipe_id": "pasta"})
        self.service.delete("pasta")

        response = self.client.get("/meal-plan")
        monday = self.day_section(response.data.decode(), "monday")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Tomato Pasta", monday)
        self.assertIn("Nothing planned.", monday)


if __name__ == "__main__":
    unittest.main()
