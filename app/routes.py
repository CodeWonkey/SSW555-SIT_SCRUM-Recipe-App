
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
        try:
            recipe = service.get(recipe_id)
        except RecipeNotFound:
            abort(404)

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
