from flask import Blueprint

result_v2 = Blueprint('result_v2', __name__)

from . import routes  # noqa: E402,F401
