from urllib.parse import urlparse

from wtforms import Form
from wtforms.fields import StringField
from wtforms.validators import InputRequired

label = "Scheme and Host"


def matches_url(options, url):
    parsed = urlparse(url)
    if parsed.scheme == options["scheme"] and parsed.hostname == options["host"]:
        return True
    else:
        return False


class OptionsForm(Form):

    scheme = StringField(label="Scheme",
                         validators=[InputRequired()])

    host = StringField(label="Host",
                       validators=[InputRequired()])
