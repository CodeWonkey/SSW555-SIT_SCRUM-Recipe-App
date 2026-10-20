import unittest

from app.services.recipes import Ingredient, Recipe, RecipeNotFound, RecipeService


def sample_service() -> RecipeService:
    return RecipeService([
        Recipe("pasta", "Tomato Pasta", [
            Ingredient("Tomatoes", 2, "cups"),
            Ingredient("Olive oil", 1, "tbsp"),
        ], ["Cook pasta", "Add sauce"], servings=2, tags={"Dinner"}),
        Recipe("soup", "Tomato Soup", [
            Ingredient("tomatoes", 1, "cups"),
            Ingredient("Water", 500, "ml"),
        ], ["Simmer"], servings=4, tags={"Lunch"}, favorite=True),
    ])


class RecipeServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = sample_service()

    def test_create_and_read_recipe(self):
        recipe = Recipe("salad", "Green Salad", [], ["Mix"], servings=1)
        self.service.create(recipe)
        self.assertEqual(self.service.get("salad").title, "Green Salad")

    def test_create_rejects_duplicate_id_and_blank_title(self):
        with self.assertRaises(ValueError):
            self.service.create(Recipe("pasta", "Other", [], [], servings=1))
        with self.assertRaises(ValueError):
            self.service.create(Recipe("blank", "  ", [], [], servings=1))

    def test_read_missing_recipe_raises_clear_error(self):
        with self.assertRaises(RecipeNotFound):
            self.service.get("missing")

    def test_update_recipe_fields(self):
        updated = self.service.update("pasta", title="Weeknight Pasta", notes="Add basil")
        self.assertEqual(updated.title, "Weeknight Pasta")
        self.assertEqual(updated.notes, "Add basil")

    def test_update_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            self.service.update("pasta", favorite=True)

    def test_invalid_update_does_not_partially_change_recipe(self):
        with self.assertRaises(ValueError):
            self.service.update("pasta", title="Changed", servings=0)
        self.assertEqual(self.service.get("pasta").title, "Tomato Pasta")
        self.assertEqual(self.service.get("pasta").servings, 2)

    def test_delete_recipe(self):
        self.service.delete("pasta")
        self.assertEqual([r.id for r in self.service.list_recipes()], ["soup"])
        with self.assertRaises(RecipeNotFound):
            self.service.get("pasta")

    def test_search_matches_title_and_ingredient_case_insensitively(self):
        self.assertEqual([r.id for r in self.service.search("TOMATO")], ["pasta", "soup"])
        self.assertEqual([r.id for r in self.service.search("olive")], ["pasta"])

    def test_search_without_query_returns_all_recipes(self):
        self.assertEqual(len(self.service.search("  ")), 2)

    def test_filter_by_tag_and_favorite(self):
        self.service.set_favorite("pasta")
        self.assertEqual([r.id for r in self.service.filter(tag="dinner")], ["pasta"])
        self.assertEqual({r.id for r in self.service.filter(favorites_only=True)}, {"pasta", "soup"})

    def test_set_and_remove_favorite(self):
        self.service.set_favorite("pasta")
        self.assertTrue(self.service.get("pasta").favorite)
        self.service.set_favorite("pasta", False)
        self.assertFalse(self.service.get("pasta").favorite)

    def test_rating_accepts_one_through_five_and_rejects_out_of_range(self):
        self.assertEqual(self.service.rate("pasta", 5).rating, 5)
        for invalid in (0, 6):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.service.rate("pasta", invalid)

    def test_serving_scaling_does_not_change_saved_recipe(self):
        scaled = self.service.scale_ingredients("pasta", 4)
        self.assertEqual([i.quantity for i in scaled], [4, 2])
        self.assertEqual(self.service.get("pasta").servings, 2)
        self.assertEqual(self.service.get("pasta").ingredients[0].quantity, 2)

    def test_serving_scaling_rejects_zero(self):
        with self.assertRaises(ValueError):
            self.service.scale_ingredients("pasta", 0)

    def test_shopping_items_combine_same_ingredient_and_unit(self):
        items = self.service.shopping_items(["pasta", "soup"])
        tomatoes = next(i for i in items if i.name.casefold() == "tomatoes")
        self.assertEqual(tomatoes.quantity, 3)
        self.assertEqual(tomatoes.unit, "cups")

    def test_pantry_suggestions_rank_by_available_ingredient_fraction(self):
        results = self.service.pantry_suggestions(["tomatoes", "olive oil"])
        self.assertEqual(results[0][0].id, "pasta")
        self.assertEqual(results[0][1], 1.0)
        self.assertEqual(results[0][2], [])
        self.assertEqual(results[1][1], 0.5)
        self.assertEqual(results[1][2], ["Water"])

    def test_empty_pantry_returns_zero_match_scores(self):
        results = self.service.pantry_suggestions([])
        self.assertTrue(all(score == 0 for _, score, _ in results))
    
    def login(self):
        self.service.login("username", "password")
        self.assertTrue(self.service.is_logged_in())
    
    def test_logout(self):
        self.service.login("username", "password")
        self.service.logout()
        self.assertFalse(self.service.is_logged_in())
       
    def delete_account(self):
        self.service.login("username", "password")
        self.service.delete_account()
        self.assertFalse(self.service.is_logged_in())
        
    def test_add_recipe_from_socials(self):
        self.service.login("username", "password")
        self.service.add_recipe_from_socials("recipe_id")
        self.assertTrue(self.service.get("recipe_id").favorite)
    

if __name__ == "__main__":
    unittest.main()
