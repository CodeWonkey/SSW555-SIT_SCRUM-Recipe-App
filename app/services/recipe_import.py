import json
import re

from bs4 import BeautifulSoup


def extract_recipe(html: str | bytes) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue

        pending = [data]

        while pending:
            item = pending.pop()

            if isinstance(item, list):
                pending.extend(reversed(item))
            elif isinstance(item, dict):
                types = item.get("@type", [])

                if types == "Recipe" or (
                    isinstance(types, list) and "Recipe" in types
                ):
                    return item

                pending.extend(reversed(list(item.values())))

    raise ValueError("No supported recipe metadata found on this page.")


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _instructions(value: object) -> list[str]:
    if isinstance(value, str):
        text = _text(value)
        return [text] if text else []
    if isinstance(value, list):
        return [step for item in value for step in _instructions(item)]
    if isinstance(value, dict):
        text = _text(value.get("text"))
        if text:
            return [text]
        return _instructions(value.get("itemListElement"))
    return []


def _tags(value: object) -> set[str]:
    if isinstance(value, list):
        return {tag for item in value for tag in _tags(item)}
    return {tag.strip() for tag in _text(value).split(",") if tag.strip()}


def build_recipe_draft(data: dict, source_url: str) -> dict:
    """Prepare editable form values without creating a saved recipe."""
    ingredients = data.get("recipeIngredient", [])
    if isinstance(ingredients, str):
        ingredients = ingredients.splitlines()
    if not isinstance(ingredients, list):
        ingredients = []

    yields = data.get("recipeYield", [])
    if not isinstance(yields, list):
        yields = [yields]
    servings = ""
    for value in yields:
        match = re.fullmatch(
            r"([1-9]\d*)\s*(?:servings?|portions?|people)?",
            str(value).strip(),
            flags=re.IGNORECASE,
        )
        if match:
            servings = int(match.group(1))
            break

    return {
        "title": _text(data.get("name")),
        "servings": servings,
        "ingredients": [
            {"name": text, "quantity": "", "unit": ""}
            for item in ingredients
            if (text := _text(item))
        ],
        "steps": _instructions(data.get("recipeInstructions")),
        "tags": (
            _tags(data.get("keywords"))
            | _tags(data.get("recipeCategory"))
            | _tags(data.get("recipeCuisine"))
        ),
        "source_link": source_url,
    }
