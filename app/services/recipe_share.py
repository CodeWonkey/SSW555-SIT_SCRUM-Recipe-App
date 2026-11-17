"""Portable recipe text for sharing outside the local app."""
from app.models import Recipe


def recipe_share_text(recipe: Recipe) -> str:
    """Share cooking details without personal notes, ratings, or reviews."""
    lines = [recipe.title, f"Servings: {recipe.servings}", "", "Ingredients"]
    for ingredient in recipe.ingredients:
        lines.append("- " + " ".join(part for part in (
            f"{ingredient.quantity:.12g}", ingredient.unit, ingredient.name
        ) if part))
    lines.extend(["", "Steps"])
    lines.extend(f"{index}. {step}" for index, step in enumerate(recipe.steps, 1))
    if recipe.source_link:
        lines.extend(["", f"Source: {recipe.source_link}"])
    return "\n".join(lines) + "\n"
