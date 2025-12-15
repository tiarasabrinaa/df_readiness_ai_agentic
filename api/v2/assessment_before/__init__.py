from flask import Blueprint

assessment_before_bp_v2 = Blueprint('assessment_before_v2', __name__)

from . import routes  # noqa: E402,F401
