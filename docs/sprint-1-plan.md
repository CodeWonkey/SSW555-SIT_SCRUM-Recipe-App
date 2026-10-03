# Sprint 1 plan

## Goal

Deliver the first usable recipe journal flow: a user can create an account, add a recipe, open its full details, and find it by recipe name or ingredient. Each selected story must meet its acceptance criteria and pass automated tests in CI.

The Trello board is https://trello.com/b/Kt5h9JzH/cs555. Estimates are provisional until the team reviews them. Assign one story per member and record the member and rotating Scrum role in Trello.

| Story | Title | Owner | Points | Development tasks | Initial test case for the assigned member |
| --- | --- | --- | ---: | --- | --- |
| US-01 | Add a new recipe | [Member 1] | 5 | Validate recipe fields; build form and save route; show new recipe in list. | Saving valid title, ingredients, steps, servings, and tags displays the recipe in the list. |
| US-02 | Create a user account | [Member 2] | 5 | Define unique account storage and password hashing; build registration form and validation; establish access after registration. | Valid registration creates an account; duplicate or invalid input is rejected and passwords are never stored in plain text. |
| US-03 | View recipe details | [Member 3] | 3 | Build detail route and template for title, ingredients, steps, servings, tags, rating, and source link; handle missing recipe ID. | Opening a saved recipe displays each field required by the acceptance criterion. |
| US-04 | Search for a recipe | [Member 4] | 3 | Search by recipe name or ingredient; add search form, results, and no-result state. | A name or ingredient query returns matching recipes, including case differences. |

US-03 and US-04 depend on US-01. Their owners can start with shared recipe fixtures and an agreed model contract, then integrate after US-01 merges. US-02 can proceed independently. Total estimate: **16 points**.

Each owner should add and commit at least one test from their own account. The current tests verify the scaffold and examples; they do not substitute for the required individual commits or completed acceptance tests. A story moves to Done after its acceptance criterion is demonstrated, tests pass in CI, and a teammate reviews the change.

## Repository setup status

This is a custom Flask/Jinja/Python scaffold, not a fork or copy of the course example starter. No example modules were removed. The GitHub Actions workflow compiles the app and runs pytest on Python 3.11 and 3.12 for pushes and pull requests. Add the team repository URL and collaborator list after publishing the scaffold to a new team repository.
