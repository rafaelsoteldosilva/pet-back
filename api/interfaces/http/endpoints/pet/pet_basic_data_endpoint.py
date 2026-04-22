# api/interfaces/http/endpoints/pet/pet_basic_data_endpoint.py

from dataclasses import asdict
from typing import Any, cast

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.exceptions import NotFound
from rest_framework import status

from api.application.pet.commands.update_pet import update_pet
from api.application.pet.queries.get_basic_pet_data import get_basic_pet_data
from api.interfaces.http.serializers.pet.update_pet_basic_data_serializer import UpdatePetBasicDataSerializer



class GetOrUpdatePetBasicDataEndpoint(APIView):

    def get(
        self,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:

        data = get_basic_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        if data is None:
            raise NotFound("Pet not found")

        return Response(asdict(data), status=status.HTTP_200_OK)
   
    def patch(
        self,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        serializer = UpdatePetBasicDataSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)

        update_pet(
            center_id=center_id,
            pet_id=pet_id,
            data=validated_data,
        )

        updated_data = get_basic_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        if updated_data is None:
            raise NotFound("Pet not found")
        

        return Response(asdict(updated_data), status=status.HTTP_200_OK)