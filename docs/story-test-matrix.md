# Story-to-test matrix

These entries use the current dependency-based Trello numbering. Some behaviors are covered in `tests/test_recipe_service.py` or `tests/test_web_smoke.py`; planned cases should be added as those stories are implemented. Use synthetic data and keep each case aligned with the story's acceptance criteria.

| Story | Suggested test cases | Starter status |
| --- | --- | --- |
| US-01 Add a new recipe | Save valid title, ingredients, steps, servings, and tags; reject blank title or invalid servings. | Service tests |
| US-02 Create a user account | Validate required fields; reject duplicate account; never store a plain-text password. | Planned |
| US-03 View recipe details | Select a recipe and display ingredients, steps, servings, tags, rating, and source link. | Planned |
| US-04 Search for a recipe | Search title and ingredient without case sensitivity; empty query returns all; unmatched query returns no results. | Service tests |
| US-05 Browse Recipes by Type | Filter by cuisine or meal category; combine multiple filters with AND behavior. | Planned |
| US-06 Log in to an existing account | Accept valid credentials; reject invalid ones; verify session boundaries. | Planned |
| US-07 Save a recipe from a social media post | Save a source URL; render it as a safe clickable link; handle malformed URLs. | Planned |
| US-08 Import a recipe from a website | Import supported fields; allow review before saving; handle invalid/unsupported URLs. | Planned |
| US-09 Sort saved recipes | Sort alphabetically and newest-first; verify sorting does not mutate recipe data. | Planned |
| US-10 Edit a recipe | Update allowed fields; persist the changed detail; reject unknown fields. | Service tests |
| US-11 Delete a recipe | Delete an existing recipe; show an empty/missing state after deletion. | Service tests |
| US-12 Save Recipe to Favorites | Save once; show “Saved” state on repeat; retain favorite state on reload. | Service tests |
| US-13 Add Recipe Ingredients to Shopping Checklist | Add each ingredient unchecked; consolidate duplicate names when units match. | Service tests (aggregation) |
| US-14 View Recipe Macros | Display calories, protein, carbohydrates, and fat; show an unavailable state when data is missing. | Planned |
| US-15 Set dietary restrictions | Save multiple restrictions; reopen and edit preferences. | Planned |
| US-16 Create a weekly meal plan | Assign recipes to days; view a full week; retain plan between sessions. | Planned |
| US-17 Scale recipe servings | Scale each ingredient proportionally; reject zero servings; keep saved amounts unchanged. | Service tests |
| US-18 Write a Recipe Review | Save review and rating; prevent flagged language from being published. | Planned |
| US-19 Track pantry ingredients | Add an ingredient and quantity; reject or merge duplicate entries; retain after restart. | Planned |
| US-20 Convert ingredient measurements | Convert supported units accurately; preserve original value; test unsupported conversions. | Planned |
| US-21 Track leftover meals | Save portions and storage date linked to recipe; reload saved leftovers. | Planned |
| US-22 Add a recipe to a cook-later list | Add once; prevent duplicates; retain list between sessions. | Planned |
| US-23 Use a cooking timer | Start, pause, reset, and alert at zero; verify timer from recipe view. | Planned |
| US-24 Share a recipe | Produce a link for the selected recipe; confirm link opens that recipe. | Planned |
| US-25 Rate a recipe | Save ratings 1 through 5; reject values outside the range; show rating in list and detail. | Service tests |
| US-26 Enable hands-free cooking mode | Advance and go back by voice command; handle microphone denial and noisy input. | Planned |
| US-27 Export saved recipes to PDF | Include title, ingredients, and instructions; render long recipes and special characters. | Planned |
| US-28 View recently cooked recipes | Add cooked date; show most recent first; retain history between sessions. | Planned |
| US-29 Filter recipes by tag or favorites | Tag filtering is case-insensitive; favorites-only returns only favorite recipes. | Service tests |
| US-30 Check Off Shopping List Items | Toggle checked state; indicate when every list item is complete. | Planned |
| US-31 Remove a Recipe from Favorites | Remove it from the saved list; ensure the recipe itself remains searchable and can be saved again. | Service tests (favorite toggle) |
| US-32 Receive ingredient expiration alerts | Warn within three days; test boundary dates and expired items. | Planned |
| US-33 Calculate estimated recipe cost | Calculate total and cost per serving; identify missing prices. | Planned |
| US-34 Add a photo to a recipe | Accept supported image types; reject invalid files; retain correct recipe association. | Planned |
| US-35 Add personal notes to a recipe | Add and edit notes; verify notes remain attached to the right recipe after reload. | Service model only |
| US-36 Suggest recipes based on available pantry items | Rank by ingredient match percentage; show missing ingredients; prompt when pantry is empty. | Service tests |
| US-37 Remove a category tag from a recipe | Remove only the chosen tag; preserve all other tags and recipe fields. | Planned |
| US-38 Edit a Submitted Review | Update the author's text/rating; show an edited indicator; enforce moderation. | Planned |
| US-39 Delete a Review | Author can delete after confirmation; another user cannot delete it. | Planned |
| US-40 Auto-generate shopping list from weekly meal plan | Combine planned-meal ingredients; merge matching name/unit pairs; preserve manual items. | Service tests (aggregation) |

## Notes for implementation

- Unit conversion should be explicit about supported ingredient/unit pairs; do not silently treat volume and weight as interchangeable.
- Pantry suggestion matching currently uses exact normalized ingredient names. Fuzzy matching needs a product decision and its own tests.
- Shopping-list aggregation currently combines normalized ingredient names only when units also match.
- Authentication, persistence, URL imports, PDF export, nutrition, and voice support remain future work.
