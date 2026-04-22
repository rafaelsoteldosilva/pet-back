# api/middleware.py

import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


logger: logging.Logger = logging.getLogger("backend_access")


class BackendAccessLogMiddleware(MiddlewareMixin):

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:

        method: str = request.method or ""
        path: str = request.get_full_path() or ""
        status: int = response.status_code

        logger.info("%s %s %s", status, method, path)

        return response


class RequestDebugMiddleware:

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:

        self.get_response: Callable[[HttpRequest], HttpResponse] = get_response

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponse:

        method: str = request.method or ""
        path: str = request.path or ""

        print("REQUEST RECEIVED:", method, path)

        response: HttpResponse = self.get_response(request)

        return response
