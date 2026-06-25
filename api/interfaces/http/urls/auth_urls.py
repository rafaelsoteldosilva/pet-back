# api/interfaces/http/urls/auth_urls.py

from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from api.interfaces.http.endpoints.auth.logout_endpoint import LogoutEndpoint
from api.interfaces.http.endpoints.auth.me_endpoint import MeEndpoint
from api.interfaces.http.endpoints.auth.pet_control_token_obtain_pair_endpoint import PetControlTokenObtainPairEndpoint


urlpatterns = [
    path("login/", PetControlTokenObtainPairEndpoint.as_view(), name="auth_login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("verify/", TokenVerifyView.as_view(), name="auth_verify"),
    path("logout/", LogoutEndpoint.as_view(), name="auth_logout"),
    path("me/", MeEndpoint.as_view(), name="auth_me"),
]
