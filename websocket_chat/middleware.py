import time
from django.conf import settings
from channels.middleware import BaseMiddleware
from django.core.cache import cache
from urllib.parse import parse_qs


class WebSocketAuthMiddleware(BaseMiddleware):
    """
    Middleware for WebSocket authentication and security
    Implements JWT validation, rate limiting, and connection management
    """

    async def __call__(self, scope, receive, send):
        # Extract query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)

        # Get JWT token from query parameters
        token = query_params.get('token', [None])[0]

        if not token:
            await send({
                'type': 'websocket.close',
                'code': 4001,
                'reason': 'Authentication token required'
            })
            return

        # Validate JWT token
        user_id = await self.validate_jwt_token(token)
        if not user_id:
            await send({
                'type': 'websocket.close',
                'code': 4001,
                'reason': 'Invalid authentication token'
            })
            return

        # Check rate limiting
        if not await self.check_rate_limit(user_id):
            await send({
                'type': 'websocket.close',
                'code': 4029,
                'reason': 'Rate limit exceeded'
            })
            return

        # Add user_id to scope
        scope['user_id'] = user_id
        scope['authenticated'] = True

        return await super().__call__(scope, receive, send)

    async def validate_jwt_token(self, token):
        """Validate JWT token using Verisafe and return user_id"""
        try:
            # Use Verisafe JWT validation
            from chirp.verisafe_jwt import verify_verisafe_jwt
            payload = verify_verisafe_jwt(token)
            user_id = payload.get('user_id') or payload.get('sub')
            return user_id
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"JWT validation failed: {str(e)}")
            print(f"🔍 JWT Validation Error: {str(e)}")
            return None

    async def check_rate_limit(self, user_id):
        """Check if user has exceeded rate limit"""
        cache_key = f"websocket_rate_limit:{user_id}"
        current_time = int(time.time())

        # Get current rate limit data
        rate_data = cache.get(cache_key, {'count': 0, 'window_start': current_time})

        # Reset window if needed
        if current_time - rate_data['window_start'] >= 60:  # 1 minute window
            rate_data = {'count': 0, 'window_start': current_time}

        # Check if limit exceeded
        if rate_data['count'] >= settings.WEBSOCKET_RATE_LIMIT:
            return False

        # Increment count
        rate_data['count'] += 1
        cache.set(cache_key, rate_data, 60)  # Cache for 1 minute

        return True


class WebSocketSecurityMiddleware(BaseMiddleware):
    """
    Additional security middleware for WebSocket connections
    Implements message size limits, connection timeouts, and sanitization
    """

    async def __call__(self, scope, receive, send):
        # Add security headers to scope
        scope['max_message_size'] = settings.WEBSOCKET_MAX_MESSAGE_SIZE
        scope['connection_timeout'] = settings.WEBSOCKET_CONNECTION_TIMEOUT
        scope['heartbeat_interval'] = settings.WEBSOCKET_HEARTBEAT_INTERVAL

        return await super().__call__(scope, receive, send)
