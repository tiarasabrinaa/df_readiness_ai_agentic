from flask import Blueprint

result = Blueprint('result', __name__)

from . import routes  # noqa: E402,F401
