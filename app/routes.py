from flask import Blueprint, render_template

from app.services.recipes import RecipeService


def create_blueprint(service: RecipeService) -> Blueprint:
    bp = Blueprint("main", __name__)

    @bp.get("/")
    def home():
        return render_template("index.html", recipes=service.list_recipes())

    return bp
