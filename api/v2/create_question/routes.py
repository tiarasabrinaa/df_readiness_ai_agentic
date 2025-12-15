from flask import Blueprint, request, jsonify
from pymongo import MongoClient

from . import assessment_before_bp

from shared.session_manager import get_or_create_session

from services.database_service import db_service

