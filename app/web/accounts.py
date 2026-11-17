"""Account and profile routes, registered on the shared main blueprint."""
from flask import render_template, request, redirect, url_for, session

from app.services.users import ALLERGIES, DIETARY_RESTRICTIONS


def _profile_context(user, error: str | None = None) -> dict:
    return {
        "user": user,
        "choices": DIETARY_RESTRICTIONS,
        "allergy_choices": ALLERGIES,
        "other_allergies": ", ".join(sorted(user.other_allergies, key=str.casefold)),
        "error": error,
    }


def register_account_routes(bp, users, current_user):
    def _safe_next(target: str | None) -> str:
        # Only allow local paths, so "next" can't be used as an open redirect.
        if target and target.startswith("/") and not target.startswith("//"):
            return target
        return url_for("main.home")

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
