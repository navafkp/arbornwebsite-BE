from django.conf import settings
from django.http import JsonResponse

from config.decorators import api_endpoint, parse_json_body

from . import services


# @api_endpoint(allowed_methods=["POST"], auth="none")
def google_auth(request):
    """POST id_token (Google's raw ID token) -> verify -> find-or-create -> JWT."""
    data = parse_json_body(request)
    id_token = data.get("id_token")
    if not id_token:
        return JsonResponse({"detail": "id_token is required."}, status=400)

    try:
        idinfo = services.verify_google_id_token(id_token)
        user = services.get_or_create_user_from_google(idinfo)
    except services.AuthError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)

    return JsonResponse(
        {**services.issue_tokens(user), "user": services.auth_user_payload(user)}
    )


# @api_endpoint(allowed_methods=["POST"], auth="none")
def refresh_token(request):
    data = parse_json_body(request)
    refresh = data.get("refresh_token")
    if not refresh:
        return JsonResponse({"detail": "refresh_token is required."}, status=400)

    try:
        access_token = services.refresh_access_token(refresh)
    except services.AuthError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)

    return JsonResponse({"access_token": access_token})


# @api_endpoint(allowed_methods=["POST"], auth="user_authentication")
def logout(request):
    data = parse_json_body(request)
    refresh = data.get("refresh_token")
    if not refresh:
        return JsonResponse({"detail": "refresh_token is required."}, status=400)

    try:
        services.blacklist_refresh_token(refresh)
    except services.AuthError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)

    return JsonResponse({"message": "Logged out successfully"})


# @api_endpoint(allowed_methods=["GET", "PATCH"], auth="user_authentication")
def me(request):
    if request.method == "PATCH":
        data = parse_json_body(request)
        services.update_me(
            request.user,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
        )
        return JsonResponse({"message": "Profile updated"})

    return JsonResponse(services.me_payload(request.user))


# @api_endpoint(allowed_methods=["POST"], auth="none")
def otp_request(request):
    data = parse_json_body(request)
    email = data.get("email")
    if not email:
        return JsonResponse({"detail": "email is required."}, status=400)

    if not services.otp_request_allowed(email):
        return JsonResponse(
            {"detail": "Too many codes requested. Try again later."}, status=429
        )

    code = services.create_otp(email)
    services.send_otp_email(email, code)

    return JsonResponse({"message": "Code sent", "expires_in": settings.OTP_TTL_SECONDS})


# @api_endpoint(allowed_methods=["POST"], auth="none")
def otp_verify(request):
    data = parse_json_body(request)
    email = data.get("email")
    code = data.get("code")
    if not email or not code:
        return JsonResponse({"detail": "email and code are required."}, status=400)

    try:
        services.verify_otp(email, code)
    except services.AuthError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)

    user = services.get_or_create_user_by_email(email)

    return JsonResponse(
        {**services.issue_tokens(user), "user": services.auth_user_payload(user)}
    )
