import uuid

from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session
from app.services.recipes import RecipeNotFound, RecipeService, Recipe, Ingredient
from app.services.users import UserService


def create_blueprint(service: RecipeService, users: UserService) -> Blueprint:
    bp = Blueprint("main", __name__)

    @bp.get("/")
    def home():
        query = request.args.get("q", "").strip()
        return render_template("index.html", recipes=service.search(query), query=query)

    @bp.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html")

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        confirmation = request.form.get("password_confirm", "")
        if password != confirmation:
            return render_template(
                "register.html",
                error="Passwords do not match",
                name=name,
                email=email,
            ), 400

        try:
            user = users.register(name=name, email=email, password=password)
        except ValueError as exc:
            return render_template(
                "register.html",
                error=str(exc),
                name=name,
                email=email,
            ), 400

        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("main.home"))

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        email = request.form.get("email", "")
        user = users.authenticate(email, request.form.get("password", ""))
        if user is None:
            return render_template(
                "login.html",
                error="Invalid email or password",
                email=email,
            ), 401

        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("main.home"))

    @bp.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("main.home"))

    @bp.get("/recipes/<recipe_id>")
    def recipe_detail(recipe_id: str):
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)
           
        return render_template("recipe_detail.html", recipe=recipe)

    @bp.route("/recipes/add", methods=["GET", "POST"])
    def add_recipe():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            servings_str = request.form.get("servings", "1")
            steps_raw = request.form.get("steps", "")
            tags_raw = request.form.get("tags", "")
            source_link = request.form.get("source_link", "").strip()

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
                    ingredients.append(
                        Ingredient(
                            name=name.strip(),
                            quantity=q_val,
                            unit=unit.strip()
                        )
                    )

            new_recipe = Recipe(
                id=str(uuid.uuid4())[:8],
                title=title,
                ingredients=ingredients,
                steps=steps,
                servings=servings,
                tags=tags,
                source_link=source_link
            )

            try:
                service.create(new_recipe)
                return redirect(url_for("main.home"))
            except ValueError as e:
                flash(str(e), "danger")

        return render_template("add_recipe.html")

    @bp.post("/recipes/<recipe_id>/shopping-list")
    def add_to_shopping_list(recipe_id: str):
        try:
            service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        selected_recipes = session.get("shopping_recipe_ids", [])

        if recipe_id not in selected_recipes:
            selected_recipes.append(recipe_id)
            session["shopping_recipe_ids"] = selected_recipes

        return redirect(url_for("main.shopping_list"))

    @bp.get("/shopping-list")
    def shopping_list():
        selected_recipes = session.get("shopping_recipe_ids", [])

        valid_recipe_ids = []

        for recipe_id in selected_recipes:
            try:
                service.get(recipe_id)
            except RecipeNotFound:
                continue

            if recipe_id not in valid_recipe_ids:
                valid_recipe_ids.append(recipe_id)

        if valid_recipe_ids != selected_recipes:
            session["shopping_recipe_ids"] = valid_recipe_ids

        items = service.shopping_items(valid_recipe_ids)

        return render_template("shopping_list.html", items=items)

    return bp

def edit_recipe():
    # Placeholder for edit recipe functionality
    pass