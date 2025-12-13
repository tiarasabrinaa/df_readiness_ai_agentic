from flask import Blueprint

start_profiling_bp = Blueprint('start_profiling', __name__)

from . import routes  # noqa: E402,F401
