import json
import logging
import uuid
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParser
from django.views.decorators.csrf import csrf_exempt
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


def parse_multipart_body(request):
    """Django only auto-parses multipart bodies for POST — this handles PATCH/PUT too."""
    if not request.content_type.startswith("multipart/form-data"):
        return {}, {}
    parser = MultiPartParser(request.META, request, request.upload_handlers, request.encoding)
    return parser.parse()


def _set_trace_id(request):
    request.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    return request.trace_id


def get_client_ip(request):
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


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

    from accounts.services import token_versions_valid

    try:
        profile = user.profile
    except ObjectDoesNotExist:
        return False, "Authentication failed. Please log in again."

    if not token_versions_valid(validated_token, profile):
        return False, "Session has been invalidated. Please log in again."

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
        @csrf_exempt
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
