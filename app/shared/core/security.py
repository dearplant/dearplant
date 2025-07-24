"""
Security utilities for JWT validation, password hashing, and encryption.
Provides comprehensive authentication and authorization functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from functools import lru_cache

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenData(BaseModel):
    """Token payload data structure"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    is_premium: Optional[bool] = False
    scopes: Optional[list] = []

class SecurityManager:
    """
    Centralized security manager for authentication and encryption.
    Handles JWT tokens, password hashing, and security validations.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.algorithm = self.settings.JWT_ALGORITHM
        self.secret_key = self.settings.JWT_SECRET_KEY
        self.access_token_expire_minutes = self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token with user data and expiration.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            
        Returns:
            str: Encoded JWT token
        """
        try:
            to_encode = data.copy()
            
            # Set expiration time
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=self.access_token_expire_minutes
                )
            
            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access"
            })
            
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            
            logger.debug(f"Access token created for user: {data.get('sub')}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token with extended expiration.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            
        Returns:
            str: Encoded JWT refresh token
        """
        try:
            to_encode = data.copy()
            
            # Set longer expiration for refresh token
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    days=self.refresh_token_expire_days
                )
            
            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh"
            })
            
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            logger.debug(f"Refresh token created for user: {data.get('sub')}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Refresh token creation failed"
            )
    
    def verify_token(
        self, 
        token: str, 
        token_type: str = "access"
    ) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access/refresh)
            
        Returns:
            dict: Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch. Expected: {token_type}, Got: {payload.get('type')}")
                raise credentials_exception
            
            # Verify expiration
            exp = payload.get("exp")
            if exp is None:
                logger.warning("Token missing expiration")
                raise credentials_exception
            
            if datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )
            
            # Get user ID
            user_id: str = payload.get("sub")
            if user_id is None:
                logger.warning("Token missing subject (user_id)")
                raise credentials_exception
            
            logger.debug(f"Token verified successfully for user: {user_id}")
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise credentials_exception
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise credentials_exception
    
    def get_password_hash(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        try:
            hashed = pwd_context.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password processing failed"
            )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Stored hashed password
            
        Returns:
            bool: True if password matches
        """
        try:
            is_valid = pwd_context.verify(plain_password, hashed_password)
            if is_valid:
                logger.debug("Password verification successful")
            else:
                logger.debug("Password verification failed")
            return is_valid
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def create_user_token_data(
        self, 
        user_id: str, 
        email: str, 
        is_active: bool = True,
        is_premium: bool = False,
        roles: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create token payload data for user.
        
        Args:
            user_id: User UUID
            email: User email
            is_active: User active status
            is_premium: Premium subscription status
            roles: User roles list
            
        Returns:
            dict: Token payload data
        """
        return {
            "sub": user_id,
            "email": email,
            "active": is_active,
            "premium": is_premium,
            "roles": roles or ["user"],
            "token_id": f"token_{user_id}_{int(datetime.utcnow().timestamp())}"
        }
    
    def validate_password_strength(self, password: str) -> tuple[bool, list]:
        """
        Validate password strength requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.debug("Password strength validation passed")
        else:
            logger.debug(f"Password strength validation failed: {errors}")
        
        return is_valid, errors
    
    def generate_api_key(self, user_id: str, purpose: str = "api_access") -> str:
        """
        Generate API key for user.
        
        Args:
            user_id: User UUID
            purpose: API key purpose
            
        Returns:
            str: API key token
        """
        try:
            data = {
                "sub": user_id,
                "purpose": purpose,
                "type": "api_key",
                "created": datetime.utcnow().isoformat()
            }
            
            # API keys don't expire by default (can be revoked)
            api_key = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"API key generated for user: {user_id}")
            return api_key
            
        except Exception as e:
            logger.error(f"API key generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key generation failed"
            )
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Verify API key and return user data.
        
        Args:
            api_key: API key to verify
            
        Returns:
            dict: API key payload data
        """
        try:
            payload = jwt.decode(
                api_key,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("type") != "api_key":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key type"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key format"
                )
            
            logger.debug(f"API key verified for user: {user_id}")
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )


# Global security manager instance
_security_manager: Optional[SecurityManager] = None


@lru_cache()
def get_security_manager() -> SecurityManager:
    """
    Get cached security manager instance.
    
    Returns:
        SecurityManager: Singleton security manager
    """
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# Convenience functions for direct usage
def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    return get_security_manager().create_access_token(data, expires_delta)


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    return get_security_manager().create_refresh_token(data, expires_delta)


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify JWT token."""
    return get_security_manager().verify_token(token, token_type)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return get_security_manager().get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return get_security_manager().verify_password(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, list]:
    """Validate password strength."""
    return get_security_manager().validate_password_strength(password)


def generate_api_key(user_id: str, purpose: str = "api_access") -> str:
    """Generate API key for user."""
    return get_security_manager().generate_api_key(user_id, purpose)


def verify_api_key(api_key: str) -> Dict[str, Any]:
    """Verify API key."""
    return get_security_manager().verify_api_key(api_key)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and return raw payload
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: Raw token payload if valid, None if invalid
    """
    try:
        security_manager = get_security_manager()
        payload = jwt.decode(token, security_manager.secret_key, algorithms=[security_manager.algorithm])
        return payload
    except JWTError:
        return None