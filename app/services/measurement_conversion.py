from __future__ import annotations

from math import isfinite

from app.services.recipes import Ingredient


# US customary measurements converted to metric units.
_CONVERSIONS = {
    "cup": (236.5882365, "mL"),
    "cups": (236.5882365, "mL"),
    "oz": (28.349523125, "g"),
    "ounce": (28.349523125, "g"),
    "ounces": (28.349523125, "g"),
    "fl oz": (29.5735295625, "mL"),
    "fluid ounce": (29.5735295625, "mL"),
    "fluid ounces": (29.5735295625, "mL"),
}


def convert_to_metric(ingredients: list[Ingredient]) -> list[Ingredient]:
    """Convert supported units without changing the original ingredients."""
    converted = []

    for ingredient in ingredients:
        unit = ingredient.unit.strip().casefold()
        conversion = _CONVERSIONS.get(unit)

        if conversion is None:
            converted.append(ingredient)
            continue

        factor, metric_unit = conversion
        quantity = ingredient.quantity * factor

        if not isfinite(quantity):
            raise ValueError("Converted ingredient amounts must be finite")

        converted.append(
            Ingredient(
                name=ingredient.name,
                quantity=round(quantity, 2),
                unit=metric_unit,
            )
        )

    return converted