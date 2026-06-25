# api/interfaces/http/endpoints/auth/pet_control_token_obtain_pair_endpoint.py

from __future__ import annotations

from rest_framework_simplejwt.views import TokenObtainPairView

from api.interfaces.http.serializers.auth.pet_control_token_obtain_pair_serializer import (
    PetControlTokenObtainPairSerializer,
)

class PetControlTokenObtainPairEndpoint(TokenObtainPairView):
    serializer_class = PetControlTokenObtainPairSerializer
