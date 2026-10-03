# CS555 Recipe Journal

A team-owned starter for the recipe journal project. It includes a runnable Flask page, a recipe service, CSS, a story-to-test planning matrix, and a notebook. The current service keeps data in memory; it is intended for prototyping and tests, not persistent storage. This scaffold was built for this project; the course example repository was not copied.

## Team members

- Ayden Malahoff-Kamei
- Vikram Prashant Gajendragadkar
- Daniel Oppenheimer
- Jocelyn Mo
- Jamie Weirick
- Turan Islamli


## Sprint 1

The proposed sprint covers US-01 (add a recipe), US-02 (create an account), US-03 (view recipe details), and US-04 (search by name or ingredient). See [`docs/sprint-1-plan.md`](docs/sprint-1-plan.md) for points, tasks, acceptance criteria, and the integration order. Assign one story to each team member and confirm the estimates together before the sprint starts.

## Get started

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flask --app app run --debug
```

Open <http://127.0.0.1:5000>. Run the tests with:

```bash
python -m pytest
```

## Project map

```text
app/                       Flask app and recipe domain service
app/services/recipes.py    In-memory recipe operations
app/templates/             Jinja page templates
app/static/css/styles.css  Shared starter styles
tests/                     Unit and web smoke tests
docs/story-test-matrix.md  Suggested test coverage for US-01–US-40
docs/sprint-1-plan.md     Proposed first sprint and test ownership
notebooks/                 Data model exploration notebook
```

## Working agreements

- Create a branch for each story. Each member should commit at least one new test case for their assigned story from their own account.
- Keep acceptance criteria visible in the issue or pull request.
- Add or update tests with each behavior change.
- Open a pull request for review; avoid committing directly to the default branch.
- Keep secrets and real user data out of the repository.

## Current limits

This scaffold has no database, authentication, recipe-detail page, or search UI. Service-level recipe creation and search are present as starting examples; the selected Sprint 1 stories still need the web flows and acceptance tests. Pantry, meal planning, shopping-list generation, and other later stories are listed in the test matrix so the team can agree on their behavior before implementing them.
