from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.recipes import RecipeService, Recipe, Ingredient
import uuid


def create_blueprint(service: RecipeService) -> Blueprint:
    bp = Blueprint("main", __name__)

    @bp.get("/")
    def home():
        return render_template("index.html", recipes=service.list_recipes())

    @bp.route("/recipes/add", methods=["GET", "POST"])
    def add_recipe():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            servings_str = request.form.get("servings", "1")
            steps_raw = request.form.get("steps", "")
            tags_raw = request.form.get("tags", "")
            
            # Parse servings safely
            try:
                servings = int(servings_str)
            except ValueError:
                servings = 1

            # Parse steps (split by newlines)
            steps = [s.strip() for s in steps_raw.split("\n") if s.strip()]

            # Parse tags (split by comma)
            tags = {t.strip() for t in tags_raw.split(",") if t.strip()}

            # Parse dynamic ingredients from form fields
            ingredient_names = request.form.getlist("ingredient_name[]")
            ingredient_quantities = request.form.getlist("ingredient_quantity[]")
            ingredient_units = request.form.getlist("ingredient_unit[]")

            ingredients = []
            for name, qty, unit in zip(ingredient_names, ingredient_quantities, ingredient_units):
                if name.strip():
                    try:
                        q_val = float(qty)
                    except ValueError:
                        q_val = 1.0
                    ingredients.append(Ingredient(name=name.strip(), quantity=q_val, unit=unit.strip()))

            # Build the Recipe object with a unique short ID
            new_recipe = Recipe(
                id=str(uuid.uuid4())[:8],
                title=title,
                ingredients=ingredients,
                steps=steps,
                servings=servings,
                tags=tags
            )

            try:
                service.create(new_recipe)
                return redirect(url_for("main.home"))
            except ValueError as e:
                flash(str(e), "danger")

        return render_template("add_recipe.html")

    return bp