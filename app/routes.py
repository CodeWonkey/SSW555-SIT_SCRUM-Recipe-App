import uuid

from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session
from app.services.meal_plan import DAYS
from app.services.recipes import RecipeNotFound, RecipeService, Recipe, Ingredient, Nutrition
from app.services.users import ALLERGIES, DIETARY_RESTRICTIONS, UserService


def _profile_context(user, error: str | None = None) -> dict:
    return {
        "user": user,
        "choices": DIETARY_RESTRICTIONS,
        "allergy_choices": ALLERGIES,
        "other_allergies": ", ".join(sorted(user.other_allergies, key=str.casefold)),
        "error": error,
    }


def create_blueprint(service: RecipeService, users: UserService) -> Blueprint:
    bp = Blueprint("main", __name__)
    PUBLIC_ENDPOINTS = {"main.login", "main.register"}

    @bp.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or "user_id" in session:
            return None
        return redirect(url_for("main.login", next=request.full_path.rstrip("?")))

    def _safe_next(target: str | None) -> str:
        # Only allow local paths, so "next" can't be used as an open redirect.
        if target and target.startswith("/") and not target.startswith("//"):
            return target
        return url_for("main.home")

    
    @bp.get("/")
    def home():
        query = request.args.get("q", "").strip()
        sort = request.args.get("sort", "newest")

        if sort not in {"newest", "az", "za"}:
            sort = "newest"

        recipes = service.search(query)

        if sort == "newest":
            recipes = list(reversed(recipes))
        else:
            recipes = sorted(
                recipes,
                key=lambda recipe: recipe.title.casefold(),
                reverse=(sort == "za")
            )

        return render_template(
            "index.html",
            recipes=recipes,
            query=query,
            sort=sort
        )

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
        return redirect(_safe_next(request.args.get("next")))

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
        return redirect(_safe_next(request.args.get("next")))

    @bp.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("main.home"))

    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        return users.get(user_id)

    @bp.route("/profile", methods=["GET", "POST"])
    def profile():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        if request.method == "POST":
            try:
                user = users.update_profile_preferences(
                    user.id,
                    request.form.getlist("dietary_restrictions"),
                    request.form.getlist("allergies"),
                    request.form.get("other_allergies", ""),
                )
            except ValueError as exc:
                return render_template(
                    "profile.html",
                    **_profile_context(users.get(user.id), error=str(exc)),
                ), 400
            return redirect(url_for("main.profile"))

        return render_template("profile.html", **_profile_context(user))

    @bp.get("/recipes/<recipe_id>")
    def recipe_detail(recipe_id: str):
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)
           
        user = current_user()
        is_saved = user is not None and recipe_id in user.favorites
        return render_template("recipe_detail.html", recipe=recipe, is_saved=is_saved)

    def _parse_recipe_form() -> dict:
        try:
            servings = int(request.form.get("servings", "1"))
        except ValueError:
            servings = 1

        ingredients = []
        for name, qty, unit in zip(
            request.form.getlist("ingredient_name[]"),
            request.form.getlist("ingredient_quantity[]"),
            request.form.getlist("ingredient_unit[]"),
        ):
            if name.strip():
                try:
                    q_val = float(qty)
                except ValueError:
                    q_val = 1.0
                ingredients.append(Ingredient(name=name.strip(), quantity=q_val, unit=unit.strip()))

        nutrition_fields = ("calories", "protein", "carbs", "fat")
        # An older client that does not submit nutrition must not erase it on edit.
        nutrition_changes = {}
        if any(name in request.form for name in nutrition_fields):
            values = [request.form.get(name, "").strip() for name in nutrition_fields]
            nutrition = None
            if any(values):
                if not all(values):
                    raise ValueError("Enter all four nutrition values, or leave all four blank")
                try:
                    nutrition = Nutrition(**dict(zip(nutrition_fields, map(float, values))))
                except ValueError:
                    raise ValueError("Nutrition values must be finite, non-negative numbers") from None
            nutrition_changes["nutrition"] = nutrition

        return {
            "title": request.form.get("title", "").strip(),
            "servings": servings,
            "steps": [s.strip() for s in request.form.get("steps", "").split("\n") if s.strip()],
            "tags": {t.strip() for t in request.form.get("tags", "").split(",") if t.strip()},
            "ingredients": ingredients,
            "source_link": request.form.get("source_link", "").strip(),
            **nutrition_changes,
        }

    @bp.route("/recipes/add", methods=["GET", "POST"])
    def add_recipe():
        if request.method == "POST":
            try:
                new_recipe = Recipe(id=str(uuid.uuid4())[:8], **_parse_recipe_form())
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

    @bp.route("/recipes/<recipe_id>/edit", methods=["GET", "POST"])
    def edit_recipe(recipe_id: str):
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        if request.method == "POST":
            try:
                service.update(recipe_id, **_parse_recipe_form())
                return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))
            except ValueError as e:
                flash(str(e), "danger")

        return render_template("add_recipe.html", recipe=recipe)
    
    @bp.post("/recipes/<recipe_id>/reviews")
    def submit_recipe_review(recipe_id: str):
        try:
            service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0

        try:
            service.add_review(
                recipe_id=recipe_id,
                author_id=session["user_id"],
                author_name=session.get("user_name", "User"),
                rating=rating,
                text=request.form.get("review", ""),
            )
            flash("Review submitted successfully.", "success")

        except ValueError as error:
            flash(str(error), "danger")

        return redirect(
            url_for("main.recipe_detail", recipe_id=recipe_id)
        )


    @bp.post("/recipes/<recipe_id>/delete")
    def delete_recipe(recipe_id: str):
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        service.delete(recipe_id)
        flash(f'Deleted "{recipe.title}".', "success")
        return redirect(url_for("main.home"))
    
    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        return users.get(user_id)

    def days_with_recipes(user):
        plan = {day: list(user.meal_plan.get(day, [])) for day, _label in DAYS}
        days = []
        changed = False
        for key, label in DAYS:
            recipes = []
            kept = []
            for recipe_id in plan[key]:
                try:
                    recipes.append(service.get(recipe_id))
                except RecipeNotFound:
                    changed = True
                    continue
                kept.append(recipe_id)
            if kept != plan[key]:
                plan[key] = kept
                changed = True
            days.append({"key": key, "label": label, "recipes": recipes})
        if changed:
            user.meal_plan = plan
        return days

    @bp.route("/meal-plan", methods=["GET", "POST"])
    def meal_plan():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        if request.method == "POST":
            recipe_id = request.form.get("recipe_id", "")
            try:
                service.get(recipe_id.strip())
            except RecipeNotFound:
                abort(404)
            try:
                users.assign_meal(user.id, request.form.get("day", ""), recipe_id)
            except ValueError as exc:
                return render_template(
                    "meal_plan.html",
                    user=user,
                    days=days_with_recipes(user),
                    recipes=service.list_recipes(),
                    error=str(exc),
                ), 400
            return redirect(url_for("main.meal_plan"))

        return render_template(
            "meal_plan.html",
            user=user,
            days=days_with_recipes(user),
            recipes=service.list_recipes(),
        )

    @bp.post("/recipes/<recipe_id>/favorite")
    def save_favorite(recipe_id: str):
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))
        try:
            service.get(recipe_id)
        except RecipeNotFound:
            abort(404)
        users.save_favorite(user.id, recipe_id)
        flash("Saved to your favorites.", "success")
        return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))

    @bp.get("/favorites")
    def favorites():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))
        recipes = []
        for recipe_id in user.favorites:
            try:
                recipes.append(service.get(recipe_id))
            except RecipeNotFound:
                continue
        return render_template("favorites.html", recipes=recipes)

    
    return bp
