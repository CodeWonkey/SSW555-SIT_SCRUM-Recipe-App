"""Shopping checklist and pantry routes."""
from flask import abort, render_template, request, redirect, url_for, flash, session

from app.services.recipes import Ingredient, RecipeNotFound


def register_inventory_routes(bp, service, users, current_user):
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
        items = _shopping_items()
        current_item_keys = {_shopping_item_key(item) for item in items}
        checked_items = set(session.get("shopping_checked_items", [])) & current_item_keys
        if checked_items != set(session.get("shopping_checked_items", [])):
            session["shopping_checked_items"] = sorted(checked_items)

        return render_template(
            "shopping_list.html", items=items, checked_items=checked_items
        )

    def _shopping_item_key(item: Ingredient) -> str:
        return f"{item.name.strip().casefold()}|{item.unit.strip().casefold()}"

    def _shopping_items() -> list[Ingredient]:
        recipe_ids = session.get("shopping_recipe_ids", [])
        valid_recipe_ids = []
        for recipe_id in recipe_ids:
            try:
                service.get(recipe_id)
            except RecipeNotFound:
                continue
            if recipe_id not in valid_recipe_ids:
                valid_recipe_ids.append(recipe_id)
        if valid_recipe_ids != recipe_ids:
            session["shopping_recipe_ids"] = valid_recipe_ids
        return service.shopping_items(valid_recipe_ids)

    @bp.post("/shopping-list/items/<int:item_index>/check")
    def check_shopping_item(item_index: int):
        """Synchronize a checked shopping item to the user's pantry once."""
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        items = _shopping_items()
        if item_index < 0 or item_index >= len(items):
            abort(404)

        item = items[item_index]
        item_key = _shopping_item_key(item)
        checked_items = set(session.get("shopping_checked_items", []))
        if request.form.get("checked"):
            if item_key not in checked_items:
                users.add_pantry_item(user.id, item.name, item.quantity, item.unit)
                checked_items.add(item_key)
                flash(f"Added {item.name} to your pantry.", "success")
        else:
            checked_items.discard(item_key)

        session["shopping_checked_items"] = sorted(checked_items)
        return redirect(url_for("main.shopping_list"))

    @bp.route("/pantry", methods=["GET", "POST"])
    def pantry():
        user = current_user()
        if user is None:
            return redirect(url_for("main.login"))

        error = None
        if request.method == "POST":
            try:
                users.add_pantry_item(
                    user.id,
                    request.form.get("name", ""),
                    request.form.get("quantity", ""),
                    request.form.get("unit", ""),
                )
                flash("Ingredient added to your pantry.", "success")
                return redirect(url_for("main.pantry"))
            except ValueError as exc:
                error = str(exc)

        return render_template("pantry.html", pantry=user.pantry, error=error)
