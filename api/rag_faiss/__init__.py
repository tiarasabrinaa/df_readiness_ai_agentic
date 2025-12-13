from flask import Blueprint

rag_faiss_bp = Blueprint('rag_faiss', __name__)

from . import routes  # noqa: E402,F401