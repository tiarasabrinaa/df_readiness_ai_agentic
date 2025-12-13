from flask import Blueprint

create_question = Blueprint('create_question', __name__)

from . import routes  # noqa: E402,F401
