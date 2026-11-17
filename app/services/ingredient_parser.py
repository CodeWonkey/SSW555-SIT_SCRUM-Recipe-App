"""Parse ingredient lines into editable name, quantity, and unit fields."""
import re


_FRACTIONS = {
    "¼": 1 / 4,
    "½": 1 / 2,
    "¾": 3 / 4,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "⅛": 1 / 8,
    "⅜": 3 / 8,
    "⅝": 5 / 8,
    "⅞": 7 / 8,
}
_UNIT_PATTERNS = (
    r"cups?", r"tablespoons?", r"tbsp\.?", r"teaspoons?", r"tsp\.?",
    r"ounces?", r"oz\.?", r"pounds?", r"lbs?\.?", r"grams?", r"g",
    r"kilograms?", r"kgs?\.?", r"millilit(?:er|re)s?", r"ml",
    r"lit(?:er|re)s?", r"l", r"cloves?", r"cans?", r"packages?", r"pkgs?\.?",
    r"slices?", r"pieces?", r"sticks?", r"pinches?", r"bunches?", r"heads?",
    r"sprigs?", r"leaves", r"fillets?", r"jars?", r"bottles?",
)
_UNIT_RE = re.compile(
    r"^(?P<unit>" + "|".join(_UNIT_PATTERNS) + r")(?:\s+|$)",
    flags=re.IGNORECASE,
)
_RANGE_RE = re.compile(r"^\d+(?:\.\d+|/\d+|\s+\d+/\d+)?\s*[-–]\s*\d")
_MIXED_FRACTION_RE = re.compile(r"^(\d+)\s+(\d+)/(\d+)\b\s*")
_FRACTION_RE = re.compile(r"^(\d+)/(\d+)\b\s*")
_UNICODE_FRACTION_RE = re.compile(r"^(\d+)?([" + "".join(_FRACTIONS) + r"])\s*")
_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)?)\b\s*")


def _parse_quantity(text: str) -> tuple[float | int | None, str]:
    """Return a leading ingredient quantity and the remaining text.

    Ranges are intentionally left intact: choosing one end of a range would
    silently change the recipe. The user can still review those lines.
    """
    if _RANGE_RE.match(text):
        return None, text

    mixed = _MIXED_FRACTION_RE.match(text)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if denominator:
            return whole + numerator / denominator, text[mixed.end():]

    fraction = _FRACTION_RE.match(text)
    if fraction:
        numerator, denominator = map(int, fraction.groups())
        if denominator:
            return numerator / denominator, text[fraction.end():]

    unicode_fraction = _UNICODE_FRACTION_RE.match(text)
    if unicode_fraction:
        whole, fraction_char = unicode_fraction.groups()
        return int(whole or 0) + _FRACTIONS[fraction_char], text[unicode_fraction.end():]

    decimal_or_whole = _NUMBER_RE.match(text)
    if decimal_or_whole:
        value = float(decimal_or_whole.group(1))
        return (int(value) if value.is_integer() else value), text[decimal_or_whole.end():]

    return None, text


def parse_ingredient(text: str) -> dict[str, float | int | str]:
    """Split a schema.org ingredient line into editable form fields."""
    ingredient = " ".join(text.split())
    quantity, remainder = _parse_quantity(ingredient)
    if quantity is None:
        return {"name": ingredient, "quantity": "", "unit": ""}

    # Package sizes are often given in parentheses before the useful unit,
    # e.g. "1 (14-ounce) can diced tomatoes".
    remainder = re.sub(r"^\([^)]*\)\s*", "", remainder)
    unit_match = _UNIT_RE.match(remainder)
    if unit_match:
        unit = unit_match.group("unit")
        name = remainder[unit_match.end():].strip(" ,")
    else:
        unit = ""
        name = remainder.strip(" ,")

    return {"name": name, "quantity": quantity, "unit": unit}
