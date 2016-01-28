from flask import Flask, jsonify, redirect, request, url_for
from flask.ext.login import LoginManager
from htmlmin.minify import html_minify

from .config import app_config
from .models import db_session, User
from .routes import routes

app = Flask(__name__)
app.secret_key = app_config["secret_key"]


@app.template_filter("format_number")
def format_number(value):
    if isinstance(value, int):
        return "{:,d}".format(value)
    else:
        return "{:,.3f}".format(value)


@app.after_request
def minify_response(response):
    if "text/html" in response.content_type:
        response.set_data(html_minify(response.get_data(as_text=True)))
    return response


@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    Close DB session when app shuts down
    http://flask.pocoo.org/docs/0.10/patterns/sqlalchemy/#declarative
    """
    db_session.remove()


login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.init_app(app)
login_manager.login_view = "routes.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.user_id == int(user_id)).first()


@login_manager.unauthorized_handler
def unauthorized():
    if "content-type" in request.headers.keys() and request.headers["content-type"] == "application/json":
        response = jsonify(status="unauthorized")
        response.status_code = 401
        return response
    else:
        return redirect(url_for("routes.login"))


app.register_blueprint(routes)
