from __future__ import annotations

DAYS = (
    ("monday", "Monday"),
    ("tuesday", "Tuesday"),
    ("wednesday", "Wednesday"),
    ("thursday", "Thursday"),
    ("friday", "Friday"),
    ("saturday", "Saturday"),
    ("sunday", "Sunday"),
)


def empty_plan() -> dict[str, list[str]]:
    return {day: [] for day, _label in DAYS}


def add_recipe(plan: dict[str, list[str]], day: str, recipe_id: str) -> dict[str, list[str]]:
    """Return a copy of the plan with the recipe assigned to that day.

    Adding the same recipe to the same day again leaves the plan unchanged.
    """
    key = day.strip().casefold()
    if key not in empty_plan():
        raise ValueError("Choose a day of the week")
    clean_id = recipe_id.strip()
    if not clean_id:
        raise ValueError("Choose a saved recipe")

    updated = {name: list(plan.get(name, [])) for name, _label in DAYS}
    if clean_id not in updated[key]:
        updated[key].append(clean_id)
    return updated
