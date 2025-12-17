from __future__ import annotations

from rest_framework.permissions import BasePermission

from .models import Application


class TokenAuthPermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        token = request.auth

        if isinstance(token, Application):
            return True

        return False
