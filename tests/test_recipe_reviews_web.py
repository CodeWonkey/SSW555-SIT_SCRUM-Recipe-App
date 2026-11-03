
import unittest

from app import create_app
from app.services.recipes import Recipe, RecipeService
from tests.tests_helpers import sign_in


class RecipeReviewsWebTests(unittest.TestCase):

    def setUp(self):
        self.service = RecipeService([
            Recipe("r1", "Pancakes", [], ["Mix", "Cook"]),
            Recipe("r2", "Pasta", [], ["Boil"]),
        ])
        self.app = create_app(self.service)
        self.client = sign_in(self.app.test_client())

    def test_submit_valid_review(self):
        response = self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "5", "review": "Great recipe!"}
        )

        self.assertEqual(response.status_code, 302)

        reviews = self.service.get("r1").reviews
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].rating, 5)
        self.assertEqual(reviews[0].text, "Great recipe!")

    def test_review_appears_on_recipe_page(self):
        self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "4", "review": "Very tasty!"}
        )

        response = self.client.get("/recipes/r1")
        self.assertIn(b"Very tasty!", response.data)
        self.assertIn(b"4/5 stars", response.data)

    def test_invalid_ratings_are_rejected(self):
        for rating in ("0", "6", "abc", "1.5"):
            with self.subTest(rating=rating):
                self.client.post(
                    "/recipes/r1/reviews",
                    data={"rating": rating, "review": "Good recipe"}
                )

        self.assertEqual(len(self.service.get("r1").reviews), 0)

    def test_empty_review_is_rejected(self):
        self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "5", "review": "   "}
        )
        self.assertEqual(len(self.service.get("r1").reviews), 0)

    def test_flagged_language_is_rejected(self):
        response = self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "1", "review": "This is STUPID."},
            follow_redirects=True
        )

        self.assertEqual(len(self.service.get("r1").reviews), 0)
        self.assertIn(b"flagged language", response.data)

    def test_reviews_stay_with_correct_recipe(self):
        self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "5", "review": "Excellent pancakes"}
        )

        self.assertEqual(len(self.service.get("r2").reviews), 0)

    def test_review_text_is_escaped(self):
        self.client.post(
            "/recipes/r1/reviews",
            data={"rating": "3", "review": "<script>alert(1)</script>"}
        )

        response = self.client.get("/recipes/r1")
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>alert(1)</script>", response.data)

    def test_unknown_recipe_returns_404(self):
        response = self.client.post(
            "/recipes/missing/reviews",
            data={"rating": "5", "review": "Good"}
        )
        self.assertEqual(response.status_code, 404)

    def test_login_is_required(self):
        response = self.app.test_client().post(
            "/recipes/r1/reviews",
            data={"rating": "5", "review": "Good"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
