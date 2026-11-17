"""Pantry validation and quantity aggregation, independent of accounts."""
from dataclasses import dataclass
from math import isfinite


@dataclass
class PantryItem:
    """An ingredient a user has available, tracked with its measurement."""

    name: str
    quantity: float
    unit: str


def add_item(items: list[PantryItem], name: str, quantity: float | str, unit: str) -> PantryItem:
    clean_name = " ".join(name.split())
    clean_unit = " ".join(unit.split())
    if not clean_name:
        raise ValueError("Ingredient name is required")
    if not clean_unit:
        raise ValueError("Unit is required")
    try:
        clean_quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValueError("Quantity must be a number") from None
    if not isfinite(clean_quantity) or clean_quantity <= 0:
        raise ValueError("Quantity must be a finite number greater than zero")

    item_key = (clean_name.casefold(), clean_unit.casefold())
    for item in items:
        if (item.name.casefold(), item.unit.casefold()) == item_key:
            item.quantity += clean_quantity
            return item

    item = PantryItem(clean_name, clean_quantity, clean_unit)
    items.append(item)
    return item
