import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class DeleteSubmittedReviewTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([Recipe("r1", "Soup", [], ["Cook"]), Recipe("r2", "Pasta", [], ["Boil"])])
        self.app = create_app(self.service)
        self.first = self.service.add_review("r1", "alice", "Alice", 5, "Excellent")
        self.second = self.service.add_review("r1", "bob", "Bob", 4, "Very good")
        self.client = sign_in(self.app.test_client(), "alice", "Alice")
        self.url = f"/recipes/r1/reviews/{self.first.id}/delete"

    def test_author_sees_delete_button_with_confirmation(self):
        page = self.client.get("/recipes/r1").get_data(as_text=True)
        self.assertIn(self.url, page)
        self.assertIn("confirm('Delete this review?", page)

    def test_author_can_delete_own_review(self):
        response = self.client.post(self.url, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Review deleted successfully", response.data)
        remaining = self.service.get("r1").reviews
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, self.second.id)
        self.assertNotIn(b"Excellent", response.data)
        self.assertIn(b"Very good", response.data)

    def test_other_user_cannot_delete_or_see_button(self):
        other = sign_in(self.app.test_client(), "bob", "Bob")
        self.assertEqual(other.post(self.url).status_code, 403)
        page = other.get("/recipes/r1").get_data(as_text=True)
        self.assertNotIn(self.url, page)
        self.assertIn(f'/recipes/r1/reviews/{self.second.id}/delete', page)
        self.assertEqual(len(self.service.get("r1").reviews), 2)

    def test_delete_only_targets_the_correct_recipe(self):
        other = self.service.add_review("r2", "alice", "Alice", 2, "Not great")
        self.client.post(self.url)
        self.assertEqual(self.service.get_review("r2", other.id).text, "Not great")

    def test_missing_recipe_or_review_returns_404(self):
        self.assertEqual(self.client.post(f"/recipes/missing/reviews/{self.first.id}/delete").status_code, 404)
        self.assertEqual(self.client.post("/recipes/r1/reviews/nonexistent/delete").status_code, 404)

    def test_cannot_delete_review_with_wrong_recipe_id(self):
        self.assertEqual(self.client.post(f"/recipes/r2/reviews/{self.first.id}/delete").status_code, 404)
        self.assertEqual(len(self.service.get("r1").reviews), 2)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_login_required(self):
        anon = self.app.test_client()
        self.assertEqual(anon.post(self.url).status_code, 302)
        self.assertEqual(len(self.service.get("r1").reviews), 2)

    def test_repeated_delete_is_404(self):
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url).status_code, 404)


if __name__ == "__main__":
    unittest.main()
