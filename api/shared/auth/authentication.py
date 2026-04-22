# api/shared/auth/authentication.py

from typing import Any
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.infrastructure.orm.models import Vet_Center_Personnel

class PersonnelJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token: Any) -> Any:
        user_id = validated_token.get("user_id")

        try:
            return Vet_Center_Personnel.objects.get(id=user_id)
        except Vet_Center_Personnel.DoesNotExist:
            raise Exception("Invalid user in JWT")
