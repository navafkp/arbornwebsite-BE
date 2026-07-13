import json
import logging
import uuid
from functools import wraps

from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

request_response_log = logging.getLogger("request_response")


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _set_trace_id(request):
    request.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    return request.trace_id


def check_user_auth(request):
    header = request.headers.get("Authorization", "")
    parts = header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False, "Authentication credentials were not provided."

    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(parts[1])
        user = jwt_auth.get_user(validated_token)
    except (InvalidToken, TokenError, AuthenticationFailed):
        return False, "Authentication failed. Please log in again."

    request.user = user
    return True, ""


def _check_auth(request, auth_mode):
    if auth_mode == "none":
        return True, ""
    if auth_mode == "user_authentication":
        return check_user_auth(request)
    return False, "Invalid authentication mode."


def api_endpoint(allowed_methods=("GET",), auth="user_authentication", log_response=True):
    """
    Wraps a plain function view with trace-id tagging, auth, method
    whitelisting, and centralized error logging. The view still builds and
    returns its own JsonResponse, so each endpoint controls its own shape.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            trace_id = _set_trace_id(request)

            if request.method not in allowed_methods:
                return JsonResponse({"detail": "Method not allowed."}, status=405)

            authenticated, message = _check_auth(request, auth)
            if not authenticated:
                return JsonResponse({"detail": message}, status=401)

            try:
                response = view_func(request, *args, **kwargs)
            except Exception as exc:
                request_response_log.error(
                    "trace_id=%s path=%s error=%s",
                    trace_id,
                    request.path,
                    exc,
                    exc_info=True,
                )
                return JsonResponse(
                    {"detail": "Something went wrong on our end. Please try again."},
                    status=500,
                )

            if log_response:
                request_response_log.info(
                    "trace_id=%s path=%s status=%s",
                    trace_id,
                    request.path,
                    getattr(response, "status_code", None),
                )
            return response

        return wrapper

    return decorator
