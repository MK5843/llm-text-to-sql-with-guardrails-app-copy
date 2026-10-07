import os
import time

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, login_manager, limiter, oauth
from models import User, QueryHistory
from llm import generate_sql
from guardrails import validate_and_prepare
from authlib.integrations.base_client.errors import OAuthError

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)
oauth.init_app(app)

if os.environ.get("GOOGLE_CLIENT_ID"):
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


# ---------- Auth ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Email and password are required.")
        return render_template("login.html", mode="register")

    if User.query.filter_by(email=email).first():
        flash("An account with that email already exists.")
        return render_template("login.html", mode="register")

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


@app.route("/login/google")
def google_login():
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/login/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except OAuthError as e:
        app.logger.warning("Google OAuth callback failed: %s", e)
        flash("Google sign-in didn't complete - please try again.")
        return redirect(url_for("login"))
    
    userinfo = token.get("userinfo") or oauth.google.parse_id_token(token)

    google_id = userinfo["sub"]
    email = userinfo["email"]

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(email=email, google_id=google_id)
        db.session.add(user)
        db.session.commit()
    elif not user.google_id:
        user.google_id = google_id
        db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------- Main app ----------

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def api_query():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400

    history = QueryHistory(user_id=current_user.id, nl_question=question)

    try:
        raw_sql = generate_sql(question)
    except Exception as e:
        app.logger.warning("LLM call failed: %s", e)
        history.status = "error"
        history.note = f"LLM error: {e}"
        db.session.add(history)
        db.session.commit()
        return jsonify({"status": "error", "reason": "Unable to generate SQL right now. LLM providers are currently unavailable or experiencing high demand. Please try again later."}), 502

    safe_sql, reason, status = validate_and_prepare(raw_sql)

    if status == "blocked":
        history.generated_sql = raw_sql
        history.status = "blocked"
        history.note = reason
        db.session.add(history)
        db.session.commit()
        # Show the generated SQL even though it's blocked - transparency about
        # what the AI attempted carries no risk, since nothing is ever run.
        return jsonify({"status": "blocked", "reason": reason, "sql": raw_sql})

    # status == "generated"
    history.generated_sql = safe_sql
    history.status = "generated"
    db.session.add(history)
    db.session.commit()

    return jsonify({"status": "generated", "sql": safe_sql})


@app.route("/api/history")
@login_required
def api_history():
    records = (
        QueryHistory.query.filter_by(user_id=current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "question": r.nl_question,
            "sql": r.generated_sql,
            "status": r.status,
            "note": r.note,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ])


if __name__ == "__main__":
    app.run(debug=True)