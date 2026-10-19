from __future__ import annotations

import os

try:
    from flask import Flask
except ModuleNotFoundError:  # Domain tests can run before web dependencies are installed.
    Flask = None  # type: ignore[assignment,misc]

from app.services.recipes import RecipeService


def create_app(service: RecipeService | None = None):
    if Flask is None:
        raise RuntimeError("Install the project dependencies with `python -m pip install -r requirements.txt`.")
    from app.routes import create_blueprint

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    app.config["RECIPE_SERVICE"] = service or RecipeService()
    app.register_blueprint(create_blueprint(app.config["RECIPE_SERVICE"]))
    return app


app = create_app() if Flask is not None else None