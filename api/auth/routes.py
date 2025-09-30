from flask import request, jsonify
from . import auth_bp
from .models import db, User
from .jwt_utils import create_tokens, decode_token
from sqlalchemy.exc import IntegrityError

@auth_bp.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    if not (username or email) or not password:
        return jsonify({'error': 'username or email and password required'}), 400
    if email:
        email = email.lower().strip()
    if username:
        username = username.strip().lower()
    user = User(email=email, username=username, full_name=full_name)
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'email already registered'}), 409
    access, refresh, refresh_jti = create_tokens(str(user.id))
    user.refresh_token_jti = refresh_jti
    db.session.commit()
    return jsonify({'user': user.to_dict(), 'access_token': access, 'refresh_token': refresh}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    data = request.get_json()
    identifier = data.get('username') or data.get('email')
    password = data.get('password', '')
    if not identifier or not password:
        return jsonify({'error': 'credentials required'}), 400
    # Try username first then email
    user = User.query.filter( (User.username==identifier.lower()) | (User.email==identifier.lower()) ).first()
    if not user or not user.verify_password(password):
        return jsonify({'error': 'invalid credentials'}), 401
    access, refresh, refresh_jti = create_tokens(str(user.id))
    user.refresh_token_jti = refresh_jti
    db.session.commit()
    return jsonify({'user': user.to_dict(), 'access_token': access, 'refresh_token': refresh})

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    data = request.get_json()
    token = data.get('refresh_token')
    if not token:
        return jsonify({'error': 'refresh_token required'}), 400
    try:
        payload = decode_token(token)
    except Exception as e:
        return jsonify({'error': 'invalid refresh token', 'detail': str(e)}), 401
    if payload.get('type') != 'refresh':
        return jsonify({'error': 'not a refresh token'}), 400
    user = User.query.get(payload['sub'])
    if not user or user.refresh_token_jti != payload.get('jti'):
        return jsonify({'error': 'refresh token revoked'}), 401
    access, new_refresh, new_jti = create_tokens(str(user.id))
    user.refresh_token_jti = new_jti
    db.session.commit()
    return jsonify({'access_token': access, 'refresh_token': new_refresh})

@auth_bp.route('/me', methods=['GET'])
def me():
    user = getattr(request, 'current_user', None)
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'user': user.to_dict()})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    user = getattr(request, 'current_user', None)
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    user.refresh_token_jti = None
    db.session.commit()
    return jsonify({'message': 'logged out'})
