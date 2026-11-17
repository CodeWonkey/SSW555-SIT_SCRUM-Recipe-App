"""US-23: Delete a review. Run AFTER US-22 has been merged into main."""
from pathlib import Path


def replace_once(path, old, new):
    file = Path(path)
    text = file.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise SystemExit(f"STOP: {path} has changed; expected code wasn't found exactly once. No change made to this file.")
    file.write_text(text.replace(old, new, 1), encoding='utf-8')


replace_once('app/services/recipes.py',
    '    def scale_ingredients(self, recipe_id: str, target_servings: int) -> list[Ingredient]:',
    '''    def delete_review(self, recipe_id: str, review_id: str, author_id: str) -> None:
        recipe = self.get(recipe_id)
        review = self.get_review(recipe_id, review_id)
        if review.author_id != author_id:
            raise ReviewPermissionDenied("Only the author can delete this review")
        recipe.reviews = [item for item in recipe.reviews if item.id != review_id]

    def scale_ingredients(self, recipe_id: str, target_servings: int) -> list[Ingredient]:''')
replace_once('app/routes.py',
    '    def _form_int(field: str) -> int:',
    '''    @bp.post("/recipes/<recipe_id>/reviews/<review_id>/delete")
    def delete_submitted_review(recipe_id: str, review_id: str):
        _get_recipe_or_404(recipe_id)
        try:
            service.delete_review(recipe_id, review_id, session["user_id"])
        except ReviewNotFound:
            abort(404)
        except ReviewPermissionDenied:
            abort(403)
        flash("Review deleted successfully.", "success")
        return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))

    def _form_int(field: str) -> int:''')
replace_once('app/templates/recipe_detail.html',
    '''              <a href="{{ url_for('main.edit_submitted_review', recipe_id=recipe.id, review_id=review.id) }}">Edit review</a>
            {% endif %}''',
    '''              <a href="{{ url_for('main.edit_submitted_review', recipe_id=recipe.id, review_id=review.id) }}">Edit review</a>
              <form method="POST" action="{{ url_for('main.delete_submitted_review', recipe_id=recipe.id, review_id=review.id) }}"
                    onsubmit="return confirm('Delete this review? This cannot be undone.');">
                <button type="submit" class="button button-danger">Delete review</button>
              </form>
            {% endif %}''')
Path('tests/test_delete_submitted_review.py').write_text('''import unittest

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
''', encoding='utf-8')
print('US-23 files updated. Run: python -m pytest tests/test_delete_submitted_review.py -q')
