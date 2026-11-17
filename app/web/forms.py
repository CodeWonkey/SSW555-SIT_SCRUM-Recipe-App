"""Convert submitted recipe fields to service values without request globals."""
from app.models import Ingredient, Nutrition


def parse_recipe_form(form, *, include_nutrition: bool = True) -> dict:
    try:
        servings = int(form.get("servings", "1"))
    except ValueError:
        servings = 1

    ingredients = []
    for name, qty, unit in zip(
        form.getlist("ingredient_name[]"),
        form.getlist("ingredient_quantity[]"),
        form.getlist("ingredient_unit[]"),
    ):
        if name.strip():
            try:
                q_val = float(qty)
            except ValueError:
                q_val = 1.0
            ingredients.append(Ingredient(name=name.strip(), quantity=q_val, unit=unit.strip()))

    nutrition_fields = ("calories", "protein", "carbs", "fat")
    # An older client that does not submit nutrition must not erase it on edit.
    nutrition_changes = {}
    if include_nutrition and any(name in form for name in nutrition_fields):
        values = [form.get(name, "").strip() for name in nutrition_fields]
        nutrition = None
        if any(values):
            if not all(values):
                raise ValueError("Enter all four nutrition values, or leave all four blank")
            try:
                nutrition = Nutrition(**dict(zip(nutrition_fields, map(float, values))))
            except ValueError:
                raise ValueError("Nutrition values must be finite, non-negative numbers") from None
        nutrition_changes["nutrition"] = nutrition

    return {
        "title": form.get("title", "").strip(),
        "servings": servings,
        "steps": [s.strip() for s in form.get("steps", "").split("\n") if s.strip()],
        "tags": {t.strip() for t in form.get("tags", "").split(",") if t.strip()},
        "ingredients": ingredients,
        "source_link": form.get("source_link", "").strip(),
        **nutrition_changes,
    }
