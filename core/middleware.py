from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from asgiref.sync import sync_to_async


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        qs = parse_qs(scope.get("query_string", b"").decode())
        token = (qs.get("token") or [None])[0]

        if token:
            user = await self._get_user(token)
            if user:
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    @sync_to_async
    def _get_user(self, token):
        try:
            jwt_auth = JWTAuthentication()
            validated = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated)
        except Exception:
            return None
