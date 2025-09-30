import os
import datetime as dt
import jwt
from typing import Tuple, Dict, Any

ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES", 15))
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES", 7))
JWT_SECRET = os.getenv("JWT_SECRET", "change_this_secret")
JWT_ALG = "HS256"

def create_tokens(user_id: str) -> Tuple[str, str, str]:
    now = dt.datetime.utcnow()
    access_payload = {
        'sub': user_id,
        'type': 'access',
        'iat': now,
        'exp': now + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    }
    refresh_jti = os.urandom(16).hex()
    refresh_payload = {
        'sub': user_id,
        'type': 'refresh',
        'jti': refresh_jti,
        'iat': now,
        'exp': now + dt.timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    }
    access = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG)
    refresh = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG)
    return access, refresh, refresh_jti

def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
