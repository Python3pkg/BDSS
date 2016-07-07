# Big Data Smart Socket
# Copyright (C) 2016 Clemson University
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import re
from datetime import timedelta

import wtforms
from flask import session
from wtforms.csrf.session import SessionCSRF

from .config import secret_key
from .models import db_session, DataSource, User
from .util import available_matcher_types, description_for_matcher_type, label_for_matcher_type
from .util import available_transfer_mechanism_types, description_for_transfer_mechanism_type, label_for_transfer_mechanism_type
from .util import available_transform_types, description_for_transform_type, label_for_transform_type


class Unique(object):
    """
    Custom validator to enforce unique values in database.
    """

    def __init__(self, model, field, scope_query=None, message=None):
        self.model = model
        self.field = field
        self.scope_query = scope_query

        if not message:
            message = "%s already taken" % field.lower().capitalize()
        self.message = message

    def __call__(self, form, field):
        query = db_session.query(self.model)
        if self.scope_query:
            query = self.scope_query(query)

        field_scope = {}
        field_scope[self.field] = field.data
        if query.filter_by(**field_scope).first():
            raise wtforms.validators.ValidationError(self.message)


class SelectWithOptionDescription(wtforms.widgets.Select):

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        if "class_" in kwargs:
            kwargs["class_"] += " option-descriptions"
        else:
            kwargs["class_"] = "option-descriptions"

        if self.multiple:
            kwargs["multiple"] = True
        html = ["<select %s>" % wtforms.widgets.html_params(name=field.name, **kwargs)]
        for val, label, selected, option_description in field.iter_choices_with_description():
            html.append(self.render_option(val, label, selected, data_description=option_description))
        html.append("</select>")
        return wtforms.widgets.HTMLString("".join(html))


class SelectWithOptionDescriptionField(wtforms.fields.SelectField):

    widget = SelectWithOptionDescription()

    def __init__(self, label=None, validators=None, coerce=wtforms.compat.text_type, choices=None, option_descriptions=None, **kwargs):
        super(SelectWithOptionDescriptionField, self).__init__(label, validators, coerce, choices, **kwargs)
        if option_descriptions:
            self.option_descriptions = option_descriptions
        else:
            self.option_descriptions = ["" for c in choices]

    def iter_choices_with_description(self):
        for (i, (value, label)) in enumerate(self.choices):
            yield (value, label, self.coerce(value) == self.data, self.option_descriptions[i])


class CSRFProtectedForm(wtforms.Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = secret_key
        csrf_time_limit = timedelta(minutes=20)

        @property
        def csrf_context(self):
            return session


class LoginForm(CSRFProtectedForm):

    email = wtforms.fields.StringField(
        label="Email Address",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Email()])

    password = wtforms.fields.PasswordField(
        label="Password",
        validators=[wtforms.validators.InputRequired()])


class RegistrationForm(CSRFProtectedForm):

    name = wtforms.fields.StringField(
        label="Name",
        validators=[wtforms.validators.InputRequired()])

    email = wtforms.fields.StringField(
        label="Email Address",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Email(), Unique(User, "email")])

    password = wtforms.fields.PasswordField(
        label="Password",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=6)])

    password_confirmation = wtforms.fields.PasswordField(
        label="Confirm Password",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.EqualTo("password", message="Passwords do not match")])


class DataSourceForm(CSRFProtectedForm):
    """
    Form for creating/editing a data source.
    """

    label = wtforms.fields.StringField(
        label="Label",
        validators=[wtforms.validators.InputRequired(), Unique(DataSource, "label")])

    description = wtforms.fields.TextAreaField(
        label="Description",
        validators=[wtforms.validators.Optional()])

    transfer_mechanism_type = SelectWithOptionDescriptionField(
        label="Transfer Mechanism",
        choices=[(t, label_for_transfer_mechanism_type(t)) for t in available_transfer_mechanism_types()],
        option_descriptions=[description_for_transfer_mechanism_type(t) for t in available_transfer_mechanism_types()],
        validators=[wtforms.validators.InputRequired()])

    transfer_mechanism_options = None


class DataSourceSearchForm(wtforms.Form):

    q = wtforms.fields.StringField(
        label="Query",
        validators=[wtforms.validators.DataRequired()])


class UrlMatcherForm(CSRFProtectedForm):
    """
    Form for creating/editing a URL matcher.
    More fields will be contained in the options forms for the various matcher types.
    """

    matcher_type = SelectWithOptionDescriptionField(
        label="Matcher Type",
        choices=[(t, label_for_matcher_type(t)) for t in available_matcher_types()],
        option_descriptions=[description_for_matcher_type(t) for t in available_matcher_types()],
        validators=[wtforms.validators.InputRequired()])

    matcher_options = None


class UrlTransformForm(CSRFProtectedForm):
    """
    Form for creating/editing a URL transform between data sources.
    More fields will be contained in the options forms for the various transform types.
    """

    to_data_source_id = wtforms.fields.SelectField(
        label="Data source to transform to",
        choices=[],
        coerce=int,
        validators=[wtforms.validators.InputRequired()])

    description = wtforms.fields.TextAreaField(
        label="Description",
        validators=[wtforms.validators.Optional()])

    transform_type = SelectWithOptionDescriptionField(
        label="Transform Type",
        choices=[(t, label_for_transform_type(t)) for t in available_transform_types()],
        option_descriptions=[description_for_transform_type(t) for t in available_transform_types()],
        validators=[wtforms.validators.InputRequired()])

    transform_options = None


class UrlForm(CSRFProtectedForm):
    """
    Form for entering URLs to check matches with data source(s) or to get transformed URLs.
    """

    url = wtforms.fields.StringField(
        label="URL",
        validators=[wtforms.validators.InputRequired()])


class FindTransfersForm(wtforms.Form):

    available_mechanisms = wtforms.fields.FieldList(
        wtforms.fields.StringField(
            label="Mechanism",
            validators=[wtforms.validators.InputRequired()]),
        label="Available Mechanisms",
        min_entries=1)

    url = wtforms.fields.StringField(
        label="URL",
        validators=[wtforms.validators.InputRequired()])


class TransferReportForm(wtforms.Form):
    """
    Form for reporting transfer times.
    """

    is_success = wtforms.BooleanField(
        false_values=('false', 'False', ''),
        label="Successful Transfer")

    url = wtforms.StringField(
        label="URL",
        validators=[wtforms.validators.InputRequired()])

    file_size_bytes = wtforms.IntegerField(
        label="File Size (bytes)",
        validators=[wtforms.validators.InputRequired()])

    transfer_duration_seconds = wtforms.FloatField(
        label="Transfer Duration (seconds)",
        validators=[wtforms.validators.InputRequired()])

    file_checksum = wtforms.StringField(
        label="MD5 Checksum")

    def validate_file_checksum(form, field):
        if form.file_size_bytes.data > 0:
            if not field.data:
                raise wtforms.ValidationError("This field is required")
            if not re.match(r"[0-9A-Fa-f]{32}", field.data):
                raise wtforms.ValidationError("Invalid checksum")

    mechanism_output = wtforms.fields.TextAreaField(
        label="Mechanism Output",
        validators=[wtforms.validators.Optional()])


class TransferTestFileForm(CSRFProtectedForm):
    """
    Form for adding test files to a data source.
    """

    url = wtforms.StringField(
        label="URL",
        validators=[wtforms.validators.InputRequired()])


class ConfirmDeleteForm(CSRFProtectedForm):
    """
    Form for confirming deletions.
    """
    pass


class ToggleUserPermissionsForm(CSRFProtectedForm):
    """
    Form for granting/revoking a user admin permissions.
    """
    pass
