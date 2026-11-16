"""Labels that tell a viewer whether a recipe meets their saved preferences."""

from __future__ import annotations

# Value stored on the recipe, then the checkbox text.
STANDARD_DIET_LABELS = (
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
    ("gluten-free", "Gluten-free"),
    ("dairy-free", "Dairy-free"),
    ("peanut-free", "Peanut-free"),
    ("tree-nut-free", "Tree-nut-free"),
    ("shellfish-free", "Shellfish-free"),
    ("egg-free", "Egg-free"),
    ("soy-free", "Soy-free"),
    ("sesame-free", "Sesame-free"),
)

# A saved preference is satisfied when the recipe has any label in its set.
# Vegan counts as vegetarian. Nothing else stands in for another diet.
_SATISFIED_BY = {
    "vegetarian": {"vegetarian", "vegan"},
    "vegan": {"vegan"},
    "gluten-free": {"gluten-free"},
    "dairy-free": {"dairy-free"},
    "peanuts": {"peanut-free"},
    "tree-nuts": {"tree-nut-free"},
    "shellfish": {"shellfish-free"},
    "eggs": {"egg-free"},
    "soy": {"soy-free"},
    "sesame": {"sesame-free"},
}


def _normalize(label: object) -> str:
    return " ".join(str(label).split()).casefold()


def _recipe_labels(recipe) -> set[str]:
    return {_normalize(label) for label in getattr(recipe, "diet_labels", ()) if _normalize(label)}


def is_unsuitable(recipe, user) -> bool:
    """True when the user saved a preference the recipe does not claim to meet."""
    if user is None:
        return False

    requirements: list[set[str]] = []
    for restriction in getattr(user, "dietary_restrictions", ()):
        requirements.append(_SATISFIED_BY.get(_normalize(restriction), set()))
    for allergy in getattr(user, "allergies", ()):
        requirements.append(_SATISFIED_BY.get(_normalize(allergy), set()))
    for allergy in getattr(user, "other_allergies", ()):
        name = _normalize(allergy)
        if name:
            requirements.append({f"{name}-free"})

    if not requirements:
        return False

    labels = _recipe_labels(recipe)
    return any(not options or labels.isdisjoint(options) for options in requirements)


def diet_label_choices(user, existing_labels=()) -> list[tuple[str, str]]:
    """Checkboxes for the standard labels, this user's custom allergies, and labels already on the recipe."""
    choices = list(STANDARD_DIET_LABELS)
    seen = {value for value, _label in choices}
    extras: list[tuple[str, str]] = []

    def add(value: object, label: object) -> None:
        key = _normalize(value)
        if not key or key in seen:
            return
        text = " ".join(str(label).split()) or key
        extras.append((key, text))
        seen.add(key)

    if user is not None:
        for allergy in sorted(user.other_allergies, key=str.casefold):
            add(f"{allergy}-free", f"{allergy}-free")
    for label in sorted(existing_labels, key=str.casefold):
        add(label, label)
    return choices + extras


def clean_diet_labels(submitted, user, existing_labels=()) -> set[str]:
    """Keep submitted labels that the form was allowed to offer."""
    allowed = {value for value, _label in diet_label_choices(user, existing_labels)}
    return {_normalize(label) for label in submitted if _normalize(label) in allowed}
