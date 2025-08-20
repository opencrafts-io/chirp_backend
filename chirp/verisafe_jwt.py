import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

def verify_verisafe_jwt(token: str):
    """
    Verifies and decodes a JWT issued by Verisafe using HS256.

    Returns:
        dict: Decoded token claims
    Raises:
        Exception: If the token is invalid or expired
    """
    print(f"🔍 JWT Token: {token}")
    try:
        payload = jwt.decode(
            token,
            getattr(settings, 'VERISAFE_API_SECRET', 'super-secret-token'),
            algorithms=["HS256"],
            audience=getattr(settings, 'VERISAFE_AUDIENCE', 'https://academia.opencrafts.io/'),
            issuer=getattr(settings, 'VERISAFE_ISSUER', 'https://verisafe.opencrafts.io/'),
        )
        return payload
    except ExpiredSignatureError as e:
        logger.error("Error while validating user token", extra={"error": str(e)})
        raise Exception("Token has expired")
    except InvalidTokenError as e:
        logger.error("Error while validating user token", extra={"error": str(e)})
        raise Exception(f"Invalid token: {str(e)}")
