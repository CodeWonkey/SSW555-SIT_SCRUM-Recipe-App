import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class EditSubmittedReviewTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([Recipe("r1", "Soup", [], ["Cook"]), Recipe("r2", "Salad", [], ["Mix"])])
        self.app = create_app(self.service)
        self.review = self.service.add_review("r1", "alice", "Alice", 3, "Quite good")
        self.client = sign_in(self.app.test_client(), "alice", "Alice")
        self.url = f"/recipes/r1/reviews/{self.review.id}/edit"

    def test_author_can_open_edit_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Quite good", response.data)

    def test_author_can_change_rating_and_text(self):
        response = self.client.post(self.url, data={"rating": "5", "review": "Now excellent"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        updated = self.service.get_review("r1", self.review.id)
        self.assertEqual((updated.rating, updated.text, updated.id), (5, "Now excellent", self.review.id))
        self.assertIn(b"Now excellent", response.data)
        self.assertIn(b"Edited", response.data)
        self.assertIn(b"Review updated successfully", response.data)
        self.assertTrue(updated.edited)

    def test_other_user_cannot_edit_or_see_edit_link(self):
        other = sign_in(self.app.test_client(), "bob", "Bob")
        self.assertEqual(other.get(self.url).status_code, 403)
        self.assertEqual(other.post(self.url, data={"rating": "1", "review": "Tampered"}).status_code, 403)
        page = other.get("/recipes/r1").get_data(as_text=True)
        self.assertNotIn(f'/recipes/r1/reviews/{self.review.id}/edit', page)
        self.assertEqual(self.service.get_review("r1", self.review.id).text, "Quite good")

    def test_author_sees_edit_link(self):
        self.assertIn(self.url, self.client.get("/recipes/r1").get_data(as_text=True))

    def test_invalid_reviews_are_rejected_and_original_preserved(self):
        for data in [
            {"rating": "0", "review": "Fine"},
            {"rating": "6", "review": "Fine"},
            {"rating": "abc", "review": "Fine"},
            {"rating": "3", "review": "  "},
            {"rating": "3", "review": "You IDIOT"},
            {"rating": "3", "review": "x" * 1001},
        ]:
            with self.subTest(data=data):
                response = self.client.post(self.url, data=data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.service.get_review("r1", self.review.id), self.review)

    def test_missing_recipe_and_review_return_404(self):
        self.assertEqual(self.client.get(f"/recipes/nope/reviews/{self.review.id}/edit").status_code, 404)
        self.assertEqual(self.client.get("/recipes/r1/reviews/nope/edit").status_code, 404)

    def test_login_required(self):
        self.assertEqual(self.app.test_client().get(self.url).status_code, 302)

    def test_different_recipe_not_affected(self):
        self.client.post(self.url, data={"rating": "4", "review": "Updated"})
        self.assertEqual(len(self.service.get("r2").reviews), 0)

    def test_text_is_html_escaped(self):
        self.client.post(self.url, data={"rating": "4", "review": "<script>alert(1)</script>"})
        page = self.client.get("/recipes/r1").data
        self.assertIn(b"&lt;script&gt;", page)
        self.assertNotIn(b"<script>alert(1)</script>", page)


if __name__ == "__main__":
    unittest.main()
