from flask import Blueprint

assessment_before_bp = Blueprint('assessment_before', __name__)

from . import routes  # noqa: E402,F401
