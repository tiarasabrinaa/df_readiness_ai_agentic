from flask import Blueprint

timeline_v2 = Blueprint('timeline_v2', __name__)

from . import routes  # noqa: E402,F401
