import unittest

from app import create_app
from app.services.recipes import RecipeService


def form_data(**overrides):
    data = {
        "title": "Pancakes",
        "servings": "4",
        "tags": "Breakfast, Easy",
        "ingredient_name[]": ["Flour", "Milk"],
        "ingredient_quantity[]": ["2", "1.5"],
        "ingredient_unit[]": ["cups", "cup"],
        "steps": "Mix dry ingredients\nAdd wet ingredients\n\nCook",
    }
    data.update(overrides)
    return data


class AddRecipeWebTests(unittest.TestCase):
    def setUp(self):
        self.service = RecipeService()
        self.app = create_app(self.service)
        self.client = self.app.test_client()
        with self.app.test_request_context():
            from flask import url_for
            self.add_url = url_for("main.add_recipe")

    def test_add_page_renders_form_with_site_layout(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 200)
        for field in (b'name="title"', b'name="servings"', b'name="tags"',
                      b'name="ingredient_name[]"', b'name="steps"'):
            self.assertIn(field, response.data)
        self.assertIn(b"styles.css", response.data)
        self.assertNotIn(b"bootstrap", response.data.lower())

    def test_valid_submission_saves_recipe_in_service(self):
        self.client.post(self.add_url, data=form_data())
        recipes = self.service.list_recipes()
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].title, "Pancakes")
        self.assertEqual(recipes[0].servings, 4)

    def test_submission_parses_ingredients_steps_and_tags(self):
        self.client.post(self.add_url, data=form_data())
        recipe = self.service.list_recipes()[0]
        self.assertEqual([(i.name, i.quantity, i.unit) for i in recipe.ingredients],
                         [("Flour", 2.0, "cups"), ("Milk", 1.5, "cup")])
        self.assertEqual(recipe.steps, ["Mix dry ingredients", "Add wet ingredients", "Cook"])
        self.assertEqual(recipe.tags, {"Breakfast", "Easy"})

    def test_new_recipe_appears_in_recipe_list(self):
        response = self.client.post(self.add_url, data=form_data(), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pancakes", response.data)
        self.assertIn(b"2 ingredients", response.data)

    def test_tags_are_optional(self):
        self.client.post(self.add_url, data=form_data(tags=""))
        self.assertEqual(self.service.list_recipes()[0].tags, set())

    def test_unit_is_optional(self):
        self.client.post(self.add_url, data=form_data(**{
            "ingredient_name[]": ["Eggs"],
            "ingredient_quantity[]": ["3"],
            "ingredient_unit[]": [""],
        }))
        self.assertEqual(self.service.list_recipes()[0].ingredients[0].unit, "")

    def test_blank_title_is_not_saved(self):
        response = self.client.post(self.add_url, data=form_data(title="   "))
        self.assertIn(response.status_code, (200, 400))
        self.assertEqual(self.service.list_recipes(), [])

    def test_invalid_servings_is_not_saved(self):
        for bad in ("0", "-2"):
            with self.subTest(servings=bad):
                self.client.post(self.add_url, data=form_data(servings=bad))
                self.assertEqual(self.service.list_recipes(), [])

    def test_home_page_links_to_add_recipe(self):
        response = self.client.get("/")
        self.assertIn(self.add_url.encode(), response.data)


    def test_add_page_has_source_link_field(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="source_link"', response.data)
        self.assertIn(b'type="url"', response.data)

    def test_social_media_link_is_saved_with_recipe(self):
        source_url = "https://www.instagram.com/reel/example123/"
        response = self.client.post(
            self.add_url,
            data=form_data(source_link=source_url)
        )

        self.assertEqual(response.status_code, 302)
        recipes = self.service.list_recipes()
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].source_link, source_url)

    def test_saved_social_media_link_is_clickable(self):
        source_url = "https://www.instagram.com/reel/example123/"
        self.client.post(
            self.add_url,
            data=form_data(source_link=source_url)
        )

        recipe = self.service.list_recipes()[0]
        response = self.client.get(f"/recipes/{recipe.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h2>Source</h2>", response.data)
        self.assertIn(f'href="{source_url}"'.encode(), response.data)

    def test_recipe_can_be_saved_without_source_link(self):
        response = self.client.post(
            self.add_url,
            data=form_data()
        )

        self.assertEqual(response.status_code, 302)
        recipes = self.service.list_recipes()
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].source_link, "")


if __name__ == "__main__":
    unittest.main()