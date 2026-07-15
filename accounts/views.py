from django.conf import settings

from config.decorators import (
    api_endpoint,
    api_response,
    get_base_url,
    get_client_ip,
    parse_json_body,
    parse_multipart_body,
)

from . import services


@api_endpoint(allowed_methods=["POST"], auth="none")
def google_auth(request):
    """POST id_token (Google's raw ID token) -> verify -> find-or-create -> JWT."""
    if not services.google_auth_allowed(get_client_ip(request)):
        return api_response(429, "Too many attempts. Try again later.")

    data = parse_json_body(request)
    id_token = data.get("id_token")
    if not id_token:
        return api_response(400, "id_token is required.")

    try:
        idinfo = services.verify_google_id_token(id_token)
        user, created = services.get_or_create_user_from_google(idinfo)
    except services.AuthError as exc:
        return api_response(exc.status_code, exc.message)

    return api_response(
        200, "Signed in successfully.", data=services.build_login_payload(user, created, get_base_url(request))
    )


@api_endpoint(allowed_methods=["POST"], auth="none")
def refresh_token(request):
    data = parse_json_body(request)
    refresh = data.get("refresh_token")
    if not refresh:
        return api_response(400, "refresh_token is required.")

    try:
        access_token = services.refresh_access_token(refresh)
    except services.AuthError as exc:
        return api_response(exc.status_code, exc.message)

    return api_response(200, "Token refreshed.", data={"access_token": access_token})


@api_endpoint(allowed_methods=["POST"], auth="user_authentication")
def logout(request):
    services.invalidate_user_sessions(request.user)
    return api_response(200, "Logged out successfully.")


@api_endpoint(allowed_methods=["GET", "PATCH"], auth="user_authentication")
def profile(request):
    if request.method == "PATCH":
        post_data, files = parse_multipart_body(request)
        data = post_data if post_data else parse_json_body(request)

        try:
            services.update_me(
                request.user,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                gender=data.get("gender"),
                date_of_birth=data.get("date_of_birth"),
                profile_image=files.get("profile_image"),
            )
        except services.AuthError as exc:
            return api_response(exc.status_code, exc.message)
        return api_response(200, "Profile updated.")

    return api_response(
        200, "Successfully fetched profile", data=services.me_payload(request.user, get_base_url(request))
    )


@api_endpoint(allowed_methods=["POST"], auth="none")
def otp_request(request):
    if not services.otp_request_allowed_for_ip(get_client_ip(request)):
        return api_response(429, "Too many requests. Try again later.")

    data = parse_json_body(request)
    email = data.get("email")
    if not email:
        return api_response(400, "email is required.")

    if not services.otp_request_allowed(email):
        return api_response(429, "Too many codes requested. Try again later.")

    code = services.create_otp(email)
    services.send_otp_email(email, code)

    return api_response(
        200, "OTP sent to your email.", data={"expires_in_seconds": settings.OTP_TTL_SECONDS}
    )


@api_endpoint(allowed_methods=["POST"], auth="none")
def otp_verify(request):
    data = parse_json_body(request)
    email = data.get("email")
    code = data.get("code")
    if not email or not code:
        return api_response(400, "email and code are required.")

    try:
        services.verify_otp(email, code)
    except services.AuthError as exc:
        return api_response(exc.status_code, exc.message)

    user, created = services.get_or_create_user_by_email(email)

    return api_response(
        200, "Signed in successfully.", data=services.build_login_payload(user, created, get_base_url(request))
    )
