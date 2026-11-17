"""Regression tests: refactor preserves edit/delete author permissions and review identity."""
import unittest

from app.services.recipes import (
    Recipe, RecipeService, ReviewNotFound, ReviewPermissionDenied,
)


class ReviewRefactorTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService([
            Recipe("r1", "Bread", [], ["Bake"]),
            Recipe("r2", "Soup", [], ["Simmer"]),
        ])
        self.first = self.service.add_review("r1", "alice", "Alice", 3, "Good")
        self.second = self.service.add_review("r1", "bob", "Bob", 4, "Nice")

    def test_edit_keeps_id_and_other_reviews(self):
        updated = self.service.edit_review("r1", self.first.id, "alice", 5, "Great")
        self.assertEqual(updated.id, self.first.id)
        self.assertTrue(updated.edited)
        self.assertEqual(updated.text, "Great")
        self.assertEqual(self.service.get_review("r1", self.second.id), self.second)

    def test_delete_keeps_other_authors_reviews(self):
        self.service.delete_review("r1", self.first.id, "alice")
        self.assertEqual([r.id for r in self.service.get("r1").reviews], [self.second.id])
        self.assertEqual(self.service.get_review("r1", self.second.id).text, "Nice")

    def test_only_author_can_edit_or_delete(self):
        with self.assertRaisesRegex(ReviewPermissionDenied, "Only the author can edit"):
            self.service.edit_review("r1", self.first.id, "bob", 1, "No")
        with self.assertRaisesRegex(ReviewPermissionDenied, "Only the author can delete"):
            self.service.delete_review("r1", self.first.id, "bob")
        self.assertEqual(self.service.get_review("r1", self.first.id), self.first)

    def test_missing_or_wrong_recipe_review_not_changed(self):
        with self.assertRaises(ReviewNotFound):
            self.service.edit_review("r2", self.first.id, "alice", 5, "No")
        with self.assertRaises(ReviewNotFound):
            self.service.delete_review("r1", "unknown", "alice")
        self.assertEqual(len(self.service.get("r1").reviews), 2)

    def test_invalid_update_keeps_original_review(self):
        with self.assertRaises(ValueError):
            self.service.edit_review("r1", self.first.id, "alice", 6, "Invalid")
        self.assertEqual(self.service.get_review("r1", self.first.id), self.first)


if __name__ == "__main__":
    unittest.main()
