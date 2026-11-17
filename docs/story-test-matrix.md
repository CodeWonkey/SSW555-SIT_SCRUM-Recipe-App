# Story-to-test matrix

Story numbers match the open lists on the [CS555 Trello board](https://trello.com/b/Kt5h9JzH/cs555). Closed duplicate backlog cards are not listed. Sprint notes, the login bug card, and the empty refactoring cards are not stories.

Use synthetic data and keep each case aligned with that story's acceptance criteria.

| Story | Suggested test cases | Current tests |
| --- | --- | --- |
| US-01 Add a new recipe | Save a valid title, ingredients, steps, servings, and tags and show the recipe in the list. Reject a blank title or invalid servings. | `tests/test_add_recipe_web.py`, `tests/test_recipe_service.py` |
| US-02 Create a user account | Accept valid registration. Reject a duplicate email and invalid fields. Never store a plain-text password. | `tests/test_register_web.py`, `tests/test_user_service.py` |
| US-03 View recipe details | Open a recipe and show its title, ingredients, steps, servings, tags, rating, and source link. A missing recipe returns the missing state. | `tests/test_web_smoke.py` |
| US-04 Search for a recipe | Match a title or ingredient without case sensitivity. A blank query returns every recipe. An unmatched query shows no results. | `tests/test_search_web.py`, `tests/test_recipe_service.py` |
| US-05 Browse Recipes by Type | Filter by cuisine or meal category. Several selected filters all have to match. | `tests/test_browse_by_type.py` |
| US-06 Log in to an existing account | Accept valid credentials. Reject invalid ones. Keep one account's session separate from another's. | `tests/test_login_web.py` |
| US-07 Save a recipe from a social media post | Save a source URL and show it as a safe clickable link. A recipe can be saved with no link. | `tests/test_add_recipe_web.py` |
| US-08 Import a recipe from a website | Fill a review step with the supported fields and save only after review. Reject an invalid or unsupported URL. | `tests/test_recipe_import.py`, `tests/test_recipe_import_web.py` |
| US-09 Sort saved recipes | Sort alphabetically and newest-first. Sorting does not change the saved recipes. | `tests/test_sort_recipes_web.py` |
| US-10 Edit a recipe | Update ingredients or steps and show the saved recipe. An invalid edit leaves the recipe unchanged. | `tests/test_edit_recipe_web.py`, `tests/test_recipe_service.py` |
| US-11 Delete a recipe | Delete a recipe so it leaves the list and can no longer be opened. | `tests/test_delete_recipe_web.py`, `tests/test_recipe_service.py` |
| US-12 Save Recipe to Favorites | Save once and show a Saved state on the detail page. Each account has its own saved list. | `tests/test_favorites_web.py` |
| US-13 Add Recipe Ingredients to Shopping Checklist | Add every ingredient unchecked. Combine the same ingredient when the units match. Adding the same recipe again does not duplicate it. | `tests/test_shopping_list_web.py` |
| US-14 View Recipe Macros | Show per-serving calories, protein, carbohydrates, and fat. Show an unavailable state when nutrition is missing. | `tests/test_nutrition.py` |
| US-15 Set dietary restrictions and allergies | Save several restrictions and common or custom allergies. Reopening the profile shows them, and saving again replaces them. | `tests/test_dietary_preferences.py` |
| US-16 Create a weekly meal plan | Assign a saved recipe to a day and show the whole week. The plan stays with the account after logout. | `tests/test_meal_plan.py` |
| US-17 Scale recipe servings | Changing 4 servings to 8 doubles every amount. Scaling down and reset work. Invalid counts are rejected, and the saved amounts stay unchanged. | `tests/test_servings.py` |
| US-18 Write a Recipe Review | Save review text and a rating on that recipe. Block flagged language before it is published. | `tests/test_recipe_reviews_web.py` |
| US-19 Track pantry ingredients | Add an ingredient and quantity. Reject or merge a duplicate. The pantry is still there after restart. | Planned |
| US-20 Convert ingredient measurements | Convert supported cups and ounces to milliliters or grams. Leave the saved recipe unchanged, and leave an unsupported unit unchanged. | Planned |
| US-21 Mark recipes that conflict with saved dietary preferences | Show "May not be suitable" on the recipe list and the recipe page when a saved diet or allergy label is missing. Vegan satisfies vegetarian. A custom allergy requires an "{allergy}-free" label. A user with no saved preferences sees no mark. | Planned |
| US-22 Edit a Submitted Review | The author can replace the text or rating. Other readers see an edited label. | Planned |
| US-23 Delete a Review | The author can delete a review after confirmation. Another user has no delete option. | Planned |
| US-24 Share a recipe | Select Share on the recipe being viewed. Share its saved cooking details through device sharing, copied text, or a downloadable text file that recipients can read without the local app. Handle unsupported or denied clipboard/sharing access and cancellation; require login and reject missing recipes. | `tests/test_share_recipe_web.py`, `tests/test_recipe_share_ui.cjs` |
| US-25 Rate a recipe | Save a rating from 1 through 5 and reject a value outside that range. Show the rating on the list and the detail page. | Service tests (`tests/test_recipe_service.py`) |
| US-26 Remove a category tag from a recipe | Remove only the chosen tag. Keep the other tags and the rest of the recipe. | Planned |
| US-27 Export saved recipes to PDF | Include the title, ingredients, and instructions. Cover a long recipe and special characters. | Planned |
| US-28 Add and view recently cooked recipes | Record that a recipe was cooked. Show the history newest first, and keep each account's history separate. | `tests/test_cooking_history.py` |
| US-29 Filter recipes by tag or favorites | Tag filtering ignores case. Favorites-only returns only favorite recipes. | `tests/test_recipe_service.py`, `tests/test_browse_by_type.py` |
| US-30 Check Off Shopping List Items | Toggle an item between checked and unchecked. Show when every item is complete. | Planned |
| US-31 Remove a Recipe from Favorites | Remove it from the saved list. The recipe stays searchable and can be saved again. | Service tests (`tests/test_recipe_service.py`) |
| US-32 Use a cooking timer | Start, pause, and reset a timer from the recipe, and alert when it reaches zero. | Planned |
| US-33 Edit a weekly meal plan | Remove a recipe from one day only. It stays in saved recipes and on any other day. An empty day shows "Nothing planned." | Planned |
| US-34 Add a photo to a recipe | Accept a supported image and reject an invalid file. The image stays with that recipe. | Planned |
| US-35 Add personal notes to a recipe | Add and edit a note. The note stays attached to that recipe. | Service model only |
| US-36 Suggest recipes based on available pantry items | Rank recipes by the share of ingredients on hand and show the missing ones. An empty pantry does not invent matches. | `tests/test_recipe_service.py` |
| US-37 Enable hands-free cooking mode | Move forward and back by voice. Handle a denied microphone and noisy input. | Planned |
| US-38 Auto-generate shopping list from weekly meal plan | Combine ingredients from the planned meals, merge a matching name and unit, and keep items that were added by hand. | Ingredient aggregation is covered in `tests/test_recipe_service.py`. Generation from the meal plan is planned. |
| US-39 Add a recipe to a cook-later list | Add a recipe once and ignore a duplicate. Removing the list entry keeps the recipe. | `tests/test_cook_later.py` |
| US-40 Receive ingredient expiration alerts | Warn when an ingredient is within three days of expiring. Cover the boundary dates and an already expired item. | Planned |
| US-41 Log in and log out of account | Sign in, log out, and sign in to a different account on the same device. | `tests/test_login_web.py` |
| US-42 Track leftover meals | Save leftover portions and a storage date for a recipe, and show them again after reload. | Planned |

## Notes for implementation

- Unit conversion should be explicit about supported ingredient and unit pairs. Do not silently treat volume and weight as interchangeable.
- Pantry suggestion matching currently uses exact normalized ingredient names. Fuzzy matching needs a product decision and its own tests.
- Shopping-list aggregation currently combines normalized ingredient names only when units also match.
- Persistence, PDF export, automatic nutrition calculation, and voice support remain future work.
