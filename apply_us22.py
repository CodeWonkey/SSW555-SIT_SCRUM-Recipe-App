"""US-22: Edit a submitted review. Run in the root of the Reciped repository."""
from pathlib import Path


def replace_once(path, old, new):
    file = Path(path)
    text = file.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise SystemExit(f"STOP: {path} has changed; expected code wasn't found exactly once. No change made to this file.")
    file.write_text(text.replace(old, new, 1), encoding='utf-8')


def insert_before(path, marker, content):
    replace_once(path, marker, content + marker)


replace_once('app/models.py',
    'from dataclasses import dataclass, field\n',
    'from dataclasses import dataclass, field\nfrom uuid import uuid4\n')
replace_once('app/models.py',
    'class Review:\n    author_id: str\n    author_name: str\n    rating: int\n    text: str\n',
    'class Review:\n    author_id: str\n    author_name: str\n    rating: int\n    text: str\n    id: str = field(default_factory=lambda: uuid4().hex)\n    edited: bool = False\n')
replace_once('app/services/recipes.py',
    'import re\n',
    'import re\nfrom dataclasses import replace\n')
replace_once('app/services/recipes.py',
    'class RecipeNotFound(KeyError):\n    """Raised when a requested recipe ID is not in the service."""\n\n',
    '''class RecipeNotFound(KeyError):
    """Raised when a requested recipe ID is not in the service."""


class ReviewNotFound(KeyError):
    """Raised when a review does not exist on the requested recipe."""


class ReviewPermissionDenied(PermissionError):
    """Raised when a user tries to change another author's review."""

''')
replace_once('app/services/recipes.py',
    '''        clean_text = text.strip()

        if not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")

        if not clean_text:
            raise ValueError("Review text cannot be empty.")

        if len(clean_text) > 1000:
            raise ValueError("Review must be 1000 characters or fewer.")

        if set(_WORD.findall(clean_text.casefold())) & _FLAGGED_WORDS:
            raise ValueError("Review contains flagged language.")

        review = Review(''',
    '''        clean_text = self._validate_review(rating, text)

        review = Review(''')
insert_before('app/services/recipes.py',
    '    def scale_ingredients(self, recipe_id: str, target_servings: int) -> list[Ingredient]:',
    '''    @staticmethod
    def _validate_review(rating: int, text: str) -> str:
        clean_text = text.strip()
        if type(rating) is not int or not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        if not clean_text:
            raise ValueError("Review text cannot be empty.")
        if len(clean_text) > 1000:
            raise ValueError("Review must be 1000 characters or fewer.")
        if set(_WORD.findall(clean_text.casefold())) & _FLAGGED_WORDS:
            raise ValueError("Review contains flagged language.")
        return clean_text

    def get_review(self, recipe_id: str, review_id: str) -> Review:
        recipe = self.get(recipe_id)
        for review in recipe.reviews:
            if review.id == review_id:
                return review
        raise ReviewNotFound(review_id)

    def edit_review(self, recipe_id: str, review_id: str,
                    author_id: str, rating: int, text: str) -> Review:
        recipe = self.get(recipe_id)
        previous = self.get_review(recipe_id, review_id)
        if previous.author_id != author_id:
            raise ReviewPermissionDenied("Only the author can edit this review")
        clean_text = self._validate_review(rating, text)
        updated = replace(previous, rating=rating, text=clean_text, edited=True)
        index = next(i for i, review in enumerate(recipe.reviews)
                     if review.id == review_id)
        recipe.reviews[index] = updated
        return updated

''')
replace_once('app/routes.py',
    'from app.services.recipes import RecipeNotFound, RecipeService, Recipe\n',
    'from app.services.recipes import RecipeNotFound, ReviewNotFound, ReviewPermissionDenied, RecipeService, Recipe\n')
insert_before('app/routes.py',
    '    def _form_int(field: str) -> int:',
    '''    @bp.route("/recipes/<recipe_id>/reviews/<review_id>/edit", methods=["GET", "POST"])
    def edit_submitted_review(recipe_id: str, review_id: str):
        recipe = _get_recipe_or_404(recipe_id)
        try:
            review = service.get_review(recipe_id, review_id)
        except ReviewNotFound:
            abort(404)
        if review.author_id != session["user_id"]:
            abort(403)

        if request.method == "POST":
            try:
                service.edit_review(
                    recipe_id, review_id, session["user_id"],
                    _form_int("rating"), request.form.get("review", ""),
                )
            except ReviewNotFound:
                abort(404)
            except ReviewPermissionDenied:
                abort(403)
            except ValueError as error:
                flash(str(error), "danger")
            else:
                flash("Review updated successfully.", "success")
                return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))

        return render_template(
            "edit_review.html",
            recipe=recipe,
            review=review,
            form_rating=request.form.get("rating", str(review.rating)),
            form_text=request.form.get("review", review.text),
        )

''')
replace_once('app/templates/recipe_detail.html',
    '            <p>{{ review.text }}</p>\n',
    '''            <p>{{ review.text }}</p>
            {% if review.edited %}<span class="field-hint">Edited</span>{% endif %}
            {% if review.author_id == session.get('user_id') %}
              <a href="{{ url_for('main.edit_submitted_review', recipe_id=recipe.id, review_id=review.id) }}">Edit review</a>
            {% endif %}
''')
Path('app/templates/edit_review.html').write_text('''{% extends "base.html" %}
{% block title %}Edit review · Recipe Journal{% endblock %}
{% block content %}
  <section class="section-heading">
    <h2>Edit your review for {{ recipe.title }}</h2>
  </section>
  <form method="POST" action="{{ url_for('main.edit_submitted_review', recipe_id=recipe.id, review_id=review.id) }}" class="recipe-form">
    <div class="form-field">
      <label for="edit-review-rating">Rating</label>
      <select id="edit-review-rating" name="rating" required>
        {% for star in range(1, 6) %}
          <option value="{{ star }}"{% if form_rating|string == star|string %} selected{% endif %}>{{ star }} star{{ 's' if star != 1 else '' }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="form-field">
      <label for="edit-review-text">Review</label>
      <textarea id="edit-review-text" name="review" rows="4" maxlength="1000" required>{{ form_text }}</textarea>
    </div>
    <button type="submit" class="button">Save changes</button>
    <a href="{{ url_for('main.recipe_detail', recipe_id=recipe.id) }}">Cancel</a>
  </form>
{% endblock %}
''', encoding='utf-8')
Path('tests/test_edit_submitted_review.py').write_text('''import unittest

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
''', encoding='utf-8')
print('US-22 files updated. Run: python -m pytest tests/test_edit_submitted_review.py -q')
