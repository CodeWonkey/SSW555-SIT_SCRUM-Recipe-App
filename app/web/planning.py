"""Meal planning, cooking history, and saved recipe routes."""
from flask import abort, render_template, request, redirect, url_for, flash

from app.services.meal_plan import DAYS
from app.services.recipes import RecipeNotFound


def register_planning_routes(bp, service, users, current_user):
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

    @bp.post("/recipes/<recipe_id>/cooked")
    def mark_recipe_cooked(recipe_id: str):
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        try:
            service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        users.mark_recipe_cooked(user.id, recipe_id)

        flash("Recipe marked as cooked.", "success")

        return redirect(
            url_for("main.cooking_history")
        )

    @bp.get("/cooking-history")
    def cooking_history():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        events = users.get_cooking_history(user.id)
        history = []

        for event in events:
            try:
                recipe = service.get(event.recipe_id)
            except RecipeNotFound:
                continue

            history.append({
                "recipe": recipe,
                "cooked_at": event.cooked_at,
            })

        return render_template(
            "cooking_history.html",
            history=history,
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

    @bp.post("/recipes/<recipe_id>/cook-later")
    def save_cook_later(recipe_id: str):
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        try:
            service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

        users.save_cook_later(user.id, recipe_id)
        flash("Recipe added to your cook-later list.", "success")

        return redirect(url_for("main.recipe_detail", recipe_id=recipe_id))

    @bp.get("/cook-later")
    def cook_later():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        recipes = []
        for recipe_id in user.cook_later:
            try:
                recipes.append(service.get(recipe_id))
            except RecipeNotFound:
                continue

        return render_template("cook_later.html", recipes=recipes)
