import uuid

from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session
from app.services.diet_labels import clean_diet_labels, diet_label_choices, is_unsuitable
from app.services.measurement_conversion import convert_to_metric
from app.services.recipe_fetch import fetch_recipe_html
from app.services.recipe_import import build_recipe_draft, extract_recipe
from app.services.recipes import RecipeNotFound, RecipeService, Recipe
from app.services.users import UserService
from app.web.accounts import register_account_routes
from app.web.forms import parse_recipe_form
from app.web.inventory import register_inventory_routes
from app.web.planning import register_planning_routes


def create_blueprint(service: RecipeService, users: UserService) -> Blueprint:
    bp = Blueprint("main", __name__)

    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        return users.get(user_id)
    
    def _get_recipe_or_404(recipe_id: str) -> Recipe:
        try:
            return service.get(recipe_id)
        except RecipeNotFound:
            abort(404)
            raise

    register_account_routes(bp, users, current_user)
    register_inventory_routes(bp, service, users, current_user)
    register_planning_routes(bp, service, users, current_user)

    PUBLIC_ENDPOINTS = {"main.login", "main.register"}

    @bp.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or "user_id" in session:
            return None
        return redirect(url_for("main.login", next=request.full_path.rstrip("?")))

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

        viewer = current_user()
        return render_template(
            "index.html",
            recipes=recipes,
            query=query,
            sort=sort,
            unsuitable_ids={
                recipe.id for recipe in recipes if is_unsuitable(recipe, viewer)
            },
        )
    
    def _requested_servings(default: int) -> int:
        if "servings" not in request.args:
            return default
        try:
            return int(request.args["servings"])
        except ValueError:
            raise ValueError("Servings must be a whole number of at least 1") from None

    def _scaled_view(recipe: Recipe):
        system = request.args.get("units", "original")
        if system not in {"original", "metric"}:
            system = "original"
        try:
            target = _requested_servings(recipe.servings)
            ingredients = service.scale_ingredients(recipe.id, target)
            if system == "metric":
                ingredients = convert_to_metric(ingredients)
        except ValueError as exc:
            return recipe.servings, recipe.ingredients, "original", str(exc)
        return target, ingredients, system, None

    @bp.get("/recipes/<recipe_id>")
    def recipe_detail(recipe_id: str):
        recipe = _get_recipe_or_404(recipe_id)

        user = current_user()
        
        target_servings, ingredients, measurement_system, error = _scaled_view(recipe)

        return render_template(
            "recipe_detail.html",
            recipe=recipe,
            is_saved=user is not None and recipe_id in user.favorites,
            ingredients=ingredients,
            target_servings=target_servings,
            servings_error=error,
            measurement_system=measurement_system,
            unsuitable=is_unsuitable(recipe, user),
        ), 400 if error else 200

    def _label_choices(existing=()):
        return diet_label_choices(current_user(), existing)

    def _recipe_form_values(*, include_nutrition: bool = True, existing_labels=()) -> dict:
        values = parse_recipe_form(request.form, include_nutrition=include_nutrition)
        values["diet_labels"] = clean_diet_labels(
            request.form.getlist("diet_labels"),
            current_user(),
            existing_labels,
        )
        return values

    @bp.route("/recipes/add", methods=["GET", "POST"])
    def add_recipe():
        if request.method == "POST":
            form_values = _recipe_form_values(include_nutrition=False)
            imported = request.form.get("_imported") == "1"
            try:
                form_values = _recipe_form_values()
            except ValueError as e:
                flash(str(e), "danger")
                return render_template(
                    "add_recipe.html",
                    draft=form_values,
                    imported=imported,
                    diet_label_choices=_label_choices(),
                )

            try:
                new_recipe = Recipe(id=str(uuid.uuid4())[:8], **form_values)
                service.create(new_recipe)
                return redirect(url_for("main.home"))
            except ValueError as e:
                return render_template(
                    "add_recipe.html",
                    draft=form_values,
                    imported=imported,
                    form_error=str(e),
                    diet_label_choices=_label_choices(),
                ), 400

        return render_template(
            "add_recipe.html",
            diet_label_choices=_label_choices(),
        )

    @bp.route("/recipes/<recipe_id>/edit", methods=["GET", "POST"])
    def edit_recipe(recipe_id: str):
        recipe = _get_recipe_or_404(recipe_id)

        if request.method == "POST":
            try:
                service.update(
                    recipe_id,
                    **_recipe_form_values(existing_labels=recipe.diet_labels),
                )
                return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))
            except ValueError as e:
                flash(str(e), "danger")

        return render_template(
            "add_recipe.html",
            recipe=recipe,
            diet_label_choices=_label_choices(recipe.diet_labels),
        )

    @bp.post("/recipes/<recipe_id>/reviews")
    def submit_recipe_review(recipe_id: str):
        _get_recipe_or_404(recipe_id)
        stars = _form_int("stars")
        rating = _form_int("rating")
        
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

    def _form_int(field: str) -> int:
        try:
            return int(request.form.get(field, ""))
        except ValueError:
            return 0

    @bp.post("/recipes/<recipe_id>/rate")
    def rate_recipe(recipe_id: str):
        _get_recipe_or_404(recipe_id)
        stars = _form_int("stars")

        try:
            service.rate(recipe_id, stars)
            flash(f"Rated recipe {stars}/5 stars.", "success")
        except ValueError as error:
            flash(str(error), "danger")

        return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))

    @bp.post("/recipes/<recipe_id>/delete")
    def delete_recipe(recipe_id: str):
        recipe = _get_recipe_or_404(recipe_id)

        service.delete(recipe_id)
        flash(f'Deleted "{recipe.title}".', "success")
        return redirect(url_for("main.home"))

    @bp.route("/recipes/import", methods=["GET", "POST"])
    def import_recipe():
        source_url = ""
        error = None

        if request.method == "POST":
            source_url = request.form.get("source_url", "").strip()
            try:
                html = fetch_recipe_html(source_url)
                draft = build_recipe_draft(extract_recipe(html), source_url)
                return render_template(
                    "add_recipe.html",
                    draft=draft,
                    imported=True,
                    diet_label_choices=_label_choices(),
                )
            except ValueError as exc:
                error = str(exc)

        return render_template(
            "import_recipe.html", source_url=source_url, error=error
        ), 400 if error else 200

    return bp
