import pytest

from app.services.recipe_import import build_recipe_draft, extract_recipe


def test_extract_recipe():
    html = """
    <html><head>
      <script type="application/ld+json">
        {
          "@type": "Recipe",
          "name": "Simple Toast",
          "recipeIngredient": ["2 slices bread"],
          "recipeInstructions": ["Toast the bread."]
        }
      </script>
    </head></html>
    """

    recipe = extract_recipe(html)

    assert recipe["name"] == "Simple Toast"
    assert recipe["recipeIngredient"] == ["2 slices bread"]


def test_draft_normalizes_sections_tags_and_servings_without_guessing_quantities():
    draft = build_recipe_draft({
        "name": "<b>Simple Toast</b>",
        "recipeIngredient": ["2 slices bread", "Butter, to taste"],
        "recipeInstructions": [
            {"@type": "HowToSection", "itemListElement": [
                {"@type": "HowToStep", "text": "<p>Toast the bread.</p>"},
                {"@type": "HowToStep", "text": "Spread butter &amp; serve."},
            ]},
            "Enjoy!",
        ],
        "recipeYield": ["1 loaf", "4 servings"],
        "keywords": ["easy, quick", "toast"],
        "recipeCategory": "Breakfast",
        "recipeCuisine": ["British"],
    }, "https://example.com/toast")

    assert draft["title"] == "Simple Toast"
    assert draft["servings"] == 4
    assert draft["steps"] == [
        "Toast the bread.", "Spread butter & serve.", "Enjoy!",
    ]
    assert draft["tags"] == {"easy", "quick", "toast", "Breakfast", "British"}
    assert draft["ingredients"] == [
        {"name": "2 slices bread", "quantity": "", "unit": ""},
        {"name": "Butter, to taste", "quantity": "", "unit": ""},
    ]
    assert draft["source_link"] == "https://example.com/toast"


@pytest.mark.parametrize("recipe_yield", [None, "1 loaf", "4-6 servings", 0])
def test_draft_leaves_uncertain_servings_for_review(recipe_yield):
    draft = build_recipe_draft({"recipeYield": recipe_yield}, "https://example.com")
    assert draft["servings"] == ""


def test_draft_handles_missing_or_malformed_optional_fields():
    draft = build_recipe_draft({
        "name": None, "recipeIngredient": 42,
        "recipeInstructions": {"unexpected": "field"},
        "keywords": {"unexpected": "field"},
    }, "https://example.com")
    assert draft["title"] == ""
    assert draft["ingredients"] == []
    assert draft["steps"] == []
    assert draft["tags"] == set()


def test_extractor_skips_broken_json_and_finds_nested_recipe():
    html = '''
    <script type="application/ld+json">not JSON</script>
    <script type="application/ld+json">
      {"@graph": [{"@type": "WebSite"},
                  {"@type": ["Recipe", "HowTo"], "name": "Toast"}]}
    </script>
    '''
    assert extract_recipe(html)["name"] == "Toast"


def test_extractor_reports_unsupported_pages():
    with pytest.raises(ValueError, match="No supported recipe metadata"):
        extract_recipe("<html><h1>No recipe here</h1></html>")
