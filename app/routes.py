from flask import Blueprint, abort, render_template

from app.services.recipes import RecipeNotFound, RecipeService


def create_blueprint(service: RecipeService) -> Blueprint:
    bp = Blueprint("main", __name__)

    @bp.get("/")
    def home():
        return render_template("index.html", recipes=service.list_recipes())

    @bp.get("/recipes/<recipe_id>")
    def recipe_detail(recipe_id: str):
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        return render_template("recipe_detail.html", recipe=recipe)

    return bp