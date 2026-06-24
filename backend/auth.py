"""
Authentication module for PMF Dashboard
Handles user login and credential validation
"""

import hashlib
import secrets
from datetime import datetime, timedelta

# Store active tokens with expiration
ACTIVE_TOKENS = {}

# Credentials (password should be hashed in production)
VALID_USERS = {
    'PMF_CAPSTONE': {
        'password_hash': hashlib.sha256('Virginia@1234'.encode()).hexdigest(),
        'description': 'Capstone Project Account'
    }
}

def hash_password(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    return stored_hash == hash_password(provided_password)

def generate_token() -> str:
    """Generate a secure authentication token"""
    return secrets.token_urlsafe(32)

def create_session(user_id: str) -> str:
    """Create a new session token for a user"""
    token = generate_token()
    ACTIVE_TOKENS[token] = {
        'user_id': user_id,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=24)
    }
    return token

def validate_token(token: str) -> dict:
    """Validate a token and return session data if valid"""
    if token not in ACTIVE_TOKENS:
        return None

    session = ACTIVE_TOKENS[token]

    # Check if token has expired
    if datetime.now() > session['expires_at']:
        del ACTIVE_TOKENS[token]
        return None

    return session

def authenticate_user(user_id: str, password: str) -> tuple:
    """
    Authenticate a user with their credentials
    Returns: (success: bool, token: str or error_message: str)
    """
    # Check if user exists
    if user_id not in VALID_USERS:
        return False, 'Invalid user ID or password'

    user = VALID_USERS[user_id]

    # Verify password
    if not verify_password(user['password_hash'], password):
        return False, 'Invalid user ID or password'

    # Create session token
    token = create_session(user_id)
    return True, token

def logout_user(token: str) -> bool:
    """Logout a user by invalidating their token"""
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
        return True
    return False
