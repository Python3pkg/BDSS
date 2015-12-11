import sys
import traceback

import wtforms
from flask import abort, Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask.ext.login import current_user, login_required, login_user, logout_user
from passlib.context import CryptContext

from .core import matching_data_source, transform_url
from .forms import DataSourceForm, TimingReportForm, TransferTestFileForm, UrlForm, UrlMatcherForm, UrlTransformForm
from .forms import LoginForm, RegistrationForm
from .models import db_engine, db_session, DataSource, UrlMatcher, TimingReport, TransferTestFile, Transform, User
from .util import available_matcher_types, options_form_class_for_matcher_type
from .util import available_transfer_mechanism_types, options_form_class_for_transfer_mechanism_type
from .util import available_transform_types, options_form_class_for_transform_type

routes = Blueprint("routes", __name__)


@routes.route("/")
def index():
    """Home page"""
    return redirect(url_for("routes.list_data_sources"))


######################################################################################################
#
# User accounts
#
######################################################################################################


pwd_context = CryptContext(schemes="bcrypt_sha256")


@routes.route("/login", methods=["GET", "POST"])
def login():
    """
    Login to the application.
    """
    print(current_user, file=sys.stderr)
    if current_user and not current_user.is_anonymous:
        return redirect(url_for("routes.index"))

    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        user = User.query.filter(User.email == form.email.data).first()
        if user and pwd_context.verify(form.password.data, user.password_hash):
            login_user(user, remember=True)
            return redirect(url_for("routes.index"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("users/login.html.jinja", form=form)


@routes.route("/register", methods=["GET", "POST"])
def register():
    """
    Register a new user account.
    """
    if current_user and not current_user.is_anonymous:
        return redirect(url_for("routes.index"))

    form = RegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        pwd_hash = pwd_context.encrypt(form.password.data)
        user = User(name=form.name.data, email=form.email.data, password_hash=pwd_hash)
        try:
            db_session.add(user)
            db_session.commit()
            login_user(user, remember=True)
            return redirect(url_for("routes.index"))
        except:
            db_session.rollback()
            flash("Unable to register", "danger")
            traceback.print_exc()

    return render_template("users/register.html.jinja", form=form)


@login_required
@routes.route("/logout")
def logout():
    """
    Logout of the application.
    """
    logout_user()
    return redirect(url_for("routes.login"))


######################################################################################################
#
# Data sources
#
######################################################################################################


@routes.route("/data_sources")
@login_required
def list_data_sources():
    """
    List all data sources in database.
    """
    data_sources = DataSource.query.all()
    return render_template("data_sources/index.html.jinja", data_sources=data_sources)


@routes.route("/data_sources/new", methods=["GET", "POST"])
@login_required
def create_data_source():
    """
    Add a new data source to the database.
    """
    form = DataSourceForm()

    if request.method == "GET":
        options_form_class = options_form_class_for_transfer_mechanism_type(form.transfer_mechanism_type.choices[0][0])
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "transfer_mechanism_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form)

    elif request.method == "POST":
        form.process(request.form)

        # Dynamically add subform for transfer mechanism options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = DataSourceForm()
        if form.transfer_mechanism_type.data:
            options_form_class = options_form_class_for_transfer_mechanism_type(form.transfer_mechanism_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "transfer_mechanism_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form)

        if form.validate():
            source = DataSource(
                label=form.label.data,
                transfer_mechanism_type=form.transfer_mechanism_type.data
            )
            if "transfer_mechanism_options" in form._fields.keys() and form._fields["transfer_mechanism_options"]:
                source.transfer_mechanism_options = form._fields["transfer_mechanism_options"].data
            else:
                source.transfer_mechanism_options = {}

            try:
                db_session.add(source)
                db_session.commit()
                flash("Data source saved", "success")
                return redirect(url_for("routes.list_data_sources"))
            except:
                db_session.rollback()
                flash("Failed to save data source", "danger")
                traceback.print_exc()

    return render_template("data_sources/new.html.jinja", form=form)


@routes.route("/data_sources/<source_id>")
@login_required
def show_data_source(source_id):
    """
    Show information about a specific data source.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    return render_template("data_sources/show.html.jinja", data_source=data_source)


@routes.route("/data_sources/<source_id>/test_match", methods=["GET", "POST"])
@login_required
def test_data_source_url_match(source_id):
    """
    Test whether or not a URL matches a data source.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    form = UrlForm(request.form)

    if request.method == "POST" and form.validate():
        if data_source.matches_url(form.url.data):
            flash("URL matches", "success")
        else:
            flash("URL does not match", "danger")

    return render_template("data_sources/test_url.html.jinja", data_source=data_source, form=form)


@routes.route("/data_sources/<source_id>/edit", methods=["GET", "POST"])
@login_required
def edit_data_source(source_id):
    """
    For GET requests, show form for editing a data source.
    For POST requests, process form and update data source in database.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()

    form = DataSourceForm()

    if request.method == "GET":
        options_form_class = options_form_class_for_transfer_mechanism_type(data_source.transfer_mechanism_type)
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "transfer_mechanism_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form, data_source)

    elif request.method == "POST":
        form.process(request.form, data_source)

        # Dynamically add subform for matcher options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = DataSourceForm()
        if form.transfer_mechanism_type.data:
            options_form_class = options_form_class_for_transfer_mechanism_type(form.transfer_mechanism_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "transfer_mechanism_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form, data_source)

        if form.validate():
            data_source.label = form.label.data
            data_source.transfer_mechanism_type = form.transfer_mechanism_type.data
            if "transfer_mechanism_options" in form._fields.keys() and form._fields["transfer_mechanism_options"]:
                data_source.transfer_mechanism_options = form._fields["transfer_mechanism_options"].data
            else:
                data_source.transfer_mechanism_options = {}

            try:
                db_session.commit()
                flash("Data source updated", "success")
                return redirect(url_for("routes.show_data_source", source_id=source_id))
            except:
                db_session.rollback()
                flash("Failed to update data source", "danger")
                traceback.print_exc()

    return render_template("data_sources/edit.html.jinja", data_source=data_source, form=form)


@routes.route("/data_sources/<source_id>/delete", methods=["GET", "POST"])
@login_required
def delete_data_source(source_id):
    data_source = DataSource.query.filter(DataSource.id == source_id).first()

    if request.method == "POST":
        try:
            db_session.delete(data_source)
            db_session.commit()
            flash("Data source deleted", "success")
            return redirect(url_for("routes.list_data_sources"))
        except:
            db_session.rollback()
            flash("Failed to delete data source", "danger")
            traceback.print_exc()

    return render_template("data_sources/delete.html.jinja", data_source=data_source)


@routes.route("/data_sources/transfer_mechanism_options_form")
@login_required
def show_transfer_mechanism_options_form():
    """
    Show options form for a specific transfer mechanism type.
    """
    transfer_mechanism_type = request.args.get("transfer_mechanism_type")
    if transfer_mechanism_type not in available_transfer_mechanism_types():
        abort(404)

    options_form_class = options_form_class_for_transfer_mechanism_type(transfer_mechanism_type)
    if options_form_class:
        class ContainerForm(wtforms.Form):
            """Placeholder form to render FormField with transfer mechanism type's options form class"""
            transfer_mechanism_options = wtforms.fields.FormField(options_form_class)

        return render_template("options_form.html.jinja", form=ContainerForm())
    else:
        return ""

######################################################################################################
#
# Matchers
#
######################################################################################################


@routes.route("/data_sources/<source_id>/matchers/new", methods=["GET", "POST"])
@login_required
def add_url_matcher(source_id):
    """
    Add a new URL matcher to a data source
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    form = UrlMatcherForm()

    if request.method == "GET":
        options_form_class = options_form_class_for_matcher_type(form.matcher_type.choices[0][0])
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "matcher_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form)

    elif request.method == "POST":
        form.process(request.form)

        # Dynamically add subform for matcher options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = UrlMatcherForm()
        if form.matcher_type.data:
            options_form_class = options_form_class_for_matcher_type(form.matcher_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "matcher_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form)

        if form.validate():
            url_matcher = UrlMatcher(
                data_source_id=data_source.id,
                matcher_type=form.matcher_type.data
            )
            if "matcher_options" in form._fields.keys() and form._fields["matcher_options"]:
                url_matcher.matcher_options = form._fields["matcher_options"].data
            else:
                url_matcher.matcher_options = {}

            if db_engine.dialect.name == "sqlite":
                url_matcher.matcher_id = len(data_source.url_matchers)

            try:
                db_session.add(url_matcher)
                db_session.commit()
                flash("Matcher saved", "success")
                return redirect(url_for("routes.show_data_source", source_id=data_source.id))
            except:
                db_session.rollback()
                flash("Failed to save matcher", "danger")
                traceback.print_exc()

    return render_template("url_matchers/new.html.jinja", data_source=data_source, form=form)


@routes.route("/data_sources/<source_id>/matchers/<matcher_id>")
@login_required
def show_url_matcher(source_id, matcher_id):
    """
    Show information about a specific matcher.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    url_matcher = UrlMatcher.query.filter((DataSource.id == source_id) & (UrlMatcher.matcher_id == matcher_id)).first()

    return render_template("url_matchers/show.html.jinja", data_source=data_source, url_matcher=url_matcher)


@routes.route("/data_sources/<source_id>/matchers/<matcher_id>/edit", methods=["GET", "POST"])
@login_required
def edit_url_matcher(source_id, matcher_id):
    """
    Edit a matcher
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    url_matcher = UrlMatcher.query.filter((DataSource.id == source_id) & (UrlMatcher.matcher_id == matcher_id)).first()
    form = UrlMatcherForm()

    if request.method == "GET":
        options_form_class = options_form_class_for_matcher_type(url_matcher.matcher_type)
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "matcher_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form, url_matcher)

    elif request.method == "POST":
        form.process(request.form, url_matcher)

        # Dynamically add subform for matcher options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = UrlMatcherForm()
        if form.matcher_type.data:
            options_form_class = options_form_class_for_matcher_type(form.matcher_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "matcher_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form, url_matcher)

        if form.validate():
            url_matcher.matcher_type = form.matcher_type.data
            if "matcher_options" in form._fields.keys() and form._fields["matcher_options"]:
                url_matcher.matcher_options = form._fields["matcher_options"].data
            else:
                url_matcher.matcher_options = {}

            try:
                db_session.commit()
                flash("Matcher updated", "success")
                return redirect(url_for("routes.show_url_matcher", source_id=data_source.id, matcher_id=url_matcher.matcher_id))
            except:
                db_session.rollback()
                flash("Failed to update matcher", "danger")
                traceback.print_exc()

    return render_template("url_matchers/edit.html.jinja", data_source=data_source, url_matcher=url_matcher, form=form)


@routes.route("/data_sources/<source_id>/matchers/<matcher_id>/delete", methods=["GET", "POST"])
@login_required
def delete_url_matcher(source_id, matcher_id):
    """
    Delete a URL matcher. Prompt for confirmation first.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    url_matcher = UrlMatcher.query.filter((DataSource.id == source_id) & (UrlMatcher.matcher_id == matcher_id)).first()

    if request.method == "POST":
        try:
            db_session.delete(url_matcher)
            db_session.commit()
            flash("Matcher deleted", "success")
            return redirect(url_for("routes.show_data_source", source_id=data_source.id))
        except:
            db_session.rollback()
            flash("Failed to delete matcher", "danger")
            traceback.print_exc()

    return render_template("url_matchers/delete.html.jinja", data_source=data_source, url_matcher=url_matcher)


@routes.route("/data_sources/matcher_options_form")
@login_required
def show_matcher_options_form():
    """
    Show options form for a specific matcher type.
    """
    matcher_type = request.args.get("matcher_type")
    if matcher_type not in available_matcher_types():
        abort(404)

    options_form_class = options_form_class_for_matcher_type(matcher_type)
    if options_form_class:
        class ContainerForm(wtforms.Form):
            """Placeholder form to render FormField with matcher type's options form class"""
            matcher_options = wtforms.fields.FormField(options_form_class)

        return render_template("options_form.html.jinja", form=ContainerForm())
    else:
        return ""


######################################################################################################
#
# Transforms
#
######################################################################################################


@routes.route("/data_sources/<source_id>/transforms/new", methods=["GET", "POST"])
@login_required
def add_transform(source_id):
    """
    Add a new URL transform to a data source
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    form = UrlTransformForm()
    form.to_data_source_id.choices = [(src.id, src.label) for src in DataSource.query.filter(DataSource.id != source_id).all()]

    if request.method == "GET":
        options_form_class = options_form_class_for_transform_type(form.transform_type.choices[0][0])
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "transform_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form)

    elif request.method == "POST":
        form.process(request.form)

        # Dynamically add subform for transform options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = UrlTransformForm()
        form2.to_data_source_id.choices = [(src.id, src.label) for src in DataSource.query.filter(DataSource.id != source_id).all()]
        if form.transform_type.data:
            options_form_class = options_form_class_for_transform_type(form.transform_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "transform_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form)

        if form.validate():
            transform = Transform(
                from_data_source_id=data_source.id,
                to_data_source_id=form.to_data_source_id.data,
                transform_type=form.transform_type.data,
                description=form.description.data
            )
            if "transform_options" in form._fields.keys() and form._fields["transform_options"]:
                transform.transform_options = form._fields["transform_options"].data
            else:
                transform.transform_options = {}

            if db_engine.dialect.name == "sqlite":
                transform.transform_id = len(data_source.transforms)

            try:
                db_session.add(transform)
                db_session.commit()
                flash("Transform saved", "success")
                return redirect(url_for("routes.show_data_source", source_id=data_source.id))
            except:
                db_session.rollback()
                flash("Failed to save transform", "danger")
                traceback.print_exc()

    return render_template("transforms/new.html.jinja", from_data_source=data_source, form=form)


@routes.route("/data_sources/<source_id>/transforms/<transform_id>")
@login_required
def show_transform(source_id, transform_id):
    """
    Show information about a specific transform.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    transform = Transform.query.filter((DataSource.id == source_id) & (Transform.transform_id == transform_id)).first()

    return render_template("transforms/show.html.jinja", from_data_source=data_source, transform=transform)


@routes.route("/data_sources/<source_id>/transforms/<transform_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transform(source_id, transform_id):
    """
    Edit a transform
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    transform = Transform.query.filter((DataSource.id == source_id) & (Transform.transform_id == transform_id)).first()
    form = UrlTransformForm()
    form.to_data_source_id.choices = [(src.id, src.label) for src in DataSource.query.filter(DataSource.id != source_id).all()]

    if request.method == "GET":
        options_form_class = options_form_class_for_transform_type(transform.transform_type)
        if options_form_class:
            wtforms.form.BaseForm.__setitem__(form, "transform_options", wtforms.fields.FormField(options_form_class))
        form.process(request.form, transform)

    elif request.method == "POST":
        form.process(request.form, transform)

        # Dynamically add subform for transform options. Fields cannot be added to a
        # Form after its process method is called, so a second form must be created.
        # https://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.__setitem__
        form2 = UrlTransformForm()
        form2.to_data_source_id.choices = [(src.id, src.label) for src in DataSource.query.filter(DataSource.id != source_id).all()]
        if form.transform_type.data:
            options_form_class = options_form_class_for_transform_type(form.transform_type.data)
            if options_form_class:
                wtforms.form.BaseForm.__setitem__(form2, "transform_options", wtforms.fields.FormField(options_form_class))

        # Load request data into new form.
        form = form2
        form.process(request.form, transform)

        if form.validate():
            transform.to_data_source_id = form.to_data_source_id.data
            transform.transform_type = form.transform_type.data
            transform.description = form.description.data

            if "transform_options" in form._fields.keys() and form._fields["transform_options"]:
                transform.transform_options = form._fields["transform_options"].data
            else:
                transform.transform_options = {}

            try:
                db_session.commit()
                flash("Transform updated", "success")
                return redirect(url_for("routes.show_transform", source_id=data_source.id, transform_id=transform.transform_id))
            except:
                db_session.rollback()
                flash("Failed to update transform", "danger")
                traceback.print_exc()

    return render_template("transforms/edit.html.jinja", from_data_source=data_source, transform=transform, form=form)


@routes.route("/data_sources/<source_id>/transforms/<transform_id>/delete", methods=["GET", "POST"])
@login_required
def delete_transform(source_id, transform_id):
    """
    Delete a URL transform. Prompt for confirmation first.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    transform = Transform.query.filter((DataSource.id == source_id) & (Transform.transform_id == transform_id)).first()

    if request.method == "POST":
        try:
            db_session.delete(transform)
            db_session.commit()
            flash("Transform deleted", "success")
            return redirect(url_for("routes.show_data_source", source_id=data_source.id))
        except:
            db_session.rollback()
            flash("Failed to delete transform", "danger")
            traceback.print_exc()

    return render_template("transforms/delete.html.jinja", from_data_source=data_source, transform=transform)


@routes.route("/data_sources/transform_options_form")
@login_required
def show_transform_options_form():
    """
    Show options form for a specific transform type.
    """
    transform_type = request.args.get("transform_type")
    if transform_type not in available_transform_types():
        abort(404)

    options_form_class = options_form_class_for_transform_type(transform_type)
    if options_form_class:
        class ContainerForm(wtforms.Form):
            """Placeholder form to render FormField with transform type's options form class"""
            transform_options = wtforms.fields.FormField(options_form_class)

        return render_template("options_form.html.jinja", form=ContainerForm())
    else:
        return ""


######################################################################################################
#
# Test files
#
######################################################################################################


@routes.route("/data_sources/<source_id>/test_files/new", methods=["GET", "POST"])
@login_required
def add_test_file(source_id):
    """
    Add a new test file to a data source
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    form = TransferTestFileForm(request.form)

    if request.method == "POST" and form.validate():
        test_file = TransferTestFile()
        form.populate_obj(test_file)
        test_file.data_source_id = data_source.id
        if db_engine.dialect.name == "sqlite":
            test_file.file_id = len(data_source.transfer_test_files)

        if data_source.matches_url(test_file.url):
            try:
                db_session.add(test_file)
                db_session.commit()
                flash("Test file saved", "success")
                return redirect(url_for("routes.show_data_source", source_id=data_source.id))
            except:
                db_session.rollback()
                flash("Failed to save test file", "danger")
                traceback.print_exc()
        else:
            # FIXME: This should be a log
            print("Test file URL does not match data source", file=sys.stderr)
            flash("Test file URL does not match data source", "danger")

    return render_template("test_files/new.html.jinja", data_source=data_source, form=form)


@routes.route("/data_sources/<source_id>/test_files/<file_id>")
@login_required
def show_test_file(source_id, file_id):
    """
    Show information about a specific test file.
    """
    test_file = TransferTestFile.query.filter((DataSource.id == source_id) & (TransferTestFile.file_id == file_id)).first()

    return render_template("test_files/show.html.jinja", test_file=test_file)


@routes.route("/data_sources/<source_id>/test_files/<file_id>/edit", methods=["GET", "POST"])
@login_required
def edit_test_file(source_id, file_id):
    """
    Edit a test file
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    test_file = TransferTestFile.query.filter((DataSource.id == source_id) & (TransferTestFile.file_id == file_id)).first()
    form = TransferTestFileForm(request.form, test_file)

    if request.method == "POST" and form.validate():
        form.populate_obj(test_file)

        if data_source.matches_url(test_file.url):
            try:
                db_session.commit()
                flash("Test file updated", "success")
                return redirect(url_for("routes.show_test_file", source_id=data_source.id, file_id=test_file.file_id))
            except:
                db_session.rollback()
                flash("Failed to update test file", "danger")
                traceback.print_exc()
        else:
            # FIXME: This should be a log
            print("Test file URL does not match data source", file=sys.stderr)
            flash("Test file URL does not match data source", "danger")

    return render_template("test_files/edit.html.jinja", test_file=test_file, form=form)


@routes.route("/data_sources/<source_id>/test_files/<file_id>/delete", methods=["GET", "POST"])
@login_required
def delete_test_file(source_id, file_id):
    """
    Delete a test file. Prompt for confirmation first.
    """
    data_source = DataSource.query.filter(DataSource.id == source_id).first()
    test_file = TransferTestFile.query.filter((DataSource.id == source_id) & (TransferTestFile.file_id == file_id)).first()

    if request.method == "POST":
        try:
            db_session.delete(test_file)
            db_session.commit()
            flash("Test file deleted", "success")
            return redirect(url_for("routes.show_data_source", source_id=data_source.id))
        except:
            db_session.rollback()
            flash("Failed to delete test file", "danger")
            traceback.print_exc()

    return render_template("test_files/delete.html.jinja", test_file=test_file)


######################################################################################################
#
# Other
#
######################################################################################################


@routes.route("/transformed_urls", methods=["GET", "POST"])
def get_transformed_urls():
    """
    Find transformed URLs for a URL.
    """
    form = UrlForm(request.form)

    results = None
    if request.method == "POST":
        error_message = None
        if form.validate():
            try:
                results = transform_url(form.url.data)
            except Exception as e:
                error_message = e.message or "Unknown error"
        else:
            error_message = "Validation error"

        if request.headers.get("Accept") == "application/json":
            return jsonify(results=results, error={"message": error_message})
        elif error_message:
            flash(error_message, "danger")

    return render_template("get_transformed_urls.html.jinja", form=form, results=results)


@routes.route("/report_transfer_timing", methods=["POST"])
def report_transfer_timing():
    """
    Report timing of a transfer.
    """
    form = TimingReportForm(request.form)
    error_message = None
    if form.validate():
        data_source = matching_data_source(form.url.data)
        if data_source:
            report = TimingReport()
            form.populate_obj(report)
            report.data_source_id = data_source.id
            if db_engine.dialect.name == "sqlite":
                report.report_id = len(data_source.timing_reports)
            try:
                db_session.add(report)
                db_session.commit()
            except:
                db_session.rollback()
                traceback.print_exc()
                error_message = "Failed to save report"
        else:
            error_message = "No data sources matches URL"
    else:
        error_message = "Invalid report"

    if error_message:
        return jsonify(success=False, error={"message": error_message})
    else:
        return jsonify(success=True, error=None)
