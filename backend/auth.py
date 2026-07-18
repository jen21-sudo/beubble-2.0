# backend/auth.py
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, Response, Cookie
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED

from config import config

# API Key Security
api_key_header = APIKeyHeader(name=config.API_KEY_HEADER, auto_error=False)

class AuthManager:
    """Authentication Manager"""
    
    @staticmethod
    def verify_api_key(api_key: str) -> bool:
        """Verify if the API key is valid"""
        if not config.API_KEY:
            # In development, allow without key
            return config.ENVIRONMENT == "development"
        
        # Secure comparison
        return hmac.compare_digest(api_key, config.API_KEY)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new secure API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify API key (required)
    Usage: Depends(get_api_key)
    """
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    if not AuthManager.verify_api_key(api_key):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key

async def optional_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Optional API key dependency
    Usage: Depends(optional_api_key)
    
    In development: allows requests without key
    In production: requires a valid key
    """
    # In development, allow requests without key
    if config.ENVIRONMENT == "development" and not api_key:
        return None
    
    # If a key is provided, verify it
    if api_key:
        if AuthManager.verify_api_key(api_key):
            return api_key
        else:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
    
    # In production, a key is required
    if config.ENVIRONMENT == "production" and not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    return None

# ============================================================
# COOKIE-BASED AUTHENTICATION
# ============================================================

class CookieAuth:
    @staticmethod
    async def set_session_cookie(response: Response, api_key: str):
        response.set_cookie(
            key=config.COOKIE_NAME,
            value=api_key,
            httponly=False,      
            secure=False,
            samesite="lax",
            max_age=86400,
            path="/",
            domain="localhost"   # ← AJOUTER
        )
    
    @staticmethod
    async def clear_session_cookie(response: Response):
        """
        Clear the session cookie
        
        Args:
            response: FastAPI Response object
        """
        response.delete_cookie(
            key=config.COOKIE_NAME,
            path="/"
        )
    
    @staticmethod
    async def get_session_key(session: Optional[str] = Cookie(None)) -> Optional[str]:
        """
        Get the API key from session cookie
        
        Args:
            session: Session cookie value
        
        Returns:
            API key if present, None otherwise
        """
        return session

# ============================================================
# AUTHENTICATION DEPENDENCY (Supports both API Key and Cookie)
# ============================================================

async def get_auth(
    api_key: Optional[str] = Security(api_key_header),
    session: Optional[str] = Cookie(None)
) -> str:
    """
    Get authentication from either API key or cookie
    
    Priority:
    1. API key (for testing/API clients)
    2. Session cookie (for web frontend)
    
    Args:
        api_key: API key from header
        session: Session cookie
    
    Returns:
        Authenticated API key
    
    Raises:
        HTTPException: 401 if not authenticated
    """
    # Priority 1: API key
    if api_key:
        if AuthManager.verify_api_key(api_key):
            return api_key
        else:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
    
    # Priority 2: Session cookie
    if session:
        if AuthManager.verify_api_key(session):
            return session
    
    # No valid authentication found
    # In development, allow without auth
    if config.ENVIRONMENT == "development":
        return "development_mode"
    
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "APIKey, Cookie"}
    )

# ============================================================
# RATE LIMITING
# ============================================================

class RateLimiter:
    """Simple rate limiting"""
    
    def __init__(self):
        self.requests = {}
    
    async def check_rate_limit(self, api_key: str, limit: int = 100, window: int = 60) -> bool:
        """
        Check rate limit
        
        Args:
            api_key: API key to check
            limit: Maximum number of requests
            window: Time window in seconds
        
        Returns:
            True if allowed, False if rate limited
        """
        if config.ENVIRONMENT == "development":
            return True
        
        now = time.time()
        if api_key not in self.requests:
            self.requests[api_key] = []
        
        # Clean old requests
        self.requests[api_key] = [
            t for t in self.requests[api_key] 
            if now - t < window
        ]
        
        if len(self.requests[api_key]) >= limit:
            return False
        
        self.requests[api_key].append(now)
        return True

# Global instance
rate_limiter = RateLimiter()

# ============================================================
# DEPENDENCY ALIASES (For backward compatibility)
# ============================================================

# These aliases make it easier to migrate existing code
get_authenticated_key = get_auth
get_cookie_session = CookieAuth.get_session_key