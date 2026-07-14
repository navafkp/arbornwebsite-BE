import secrets
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_date
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from utils.common_utils import GENDER_CHOICES

from .models import OTP, SYSTEM_CONFIG_CACHE_TTL, SystemConfig, UserProfile

VALID_GENDERS = {choice[0] for choice in GENDER_CHOICES}


class AuthError(Exception):
    """Raised for any auth failure that should become an error JSON response."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def verify_google_id_token(token):
    try:
        return google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise AuthError("Invalid Google ID token.", status_code=401)


def google_auth_allowed(client_ip):
    max_requests = get_config_int(
        "google_auth_max_requests_per_window", settings.GOOGLE_AUTH_MAX_REQUESTS_PER_WINDOW
    )
    window_seconds = get_config_int(
        "google_auth_request_window_seconds", settings.GOOGLE_AUTH_REQUEST_WINDOW_SECONDS
    )
    cache_key = f"google_auth_rl:{client_ip}"
    count = cache.get(cache_key, 0)
    if count >= max_requests:
        return False
    cache.set(cache_key, count + 1, timeout=window_seconds)
    return True


def _fetch_google_profile_image(picture_url):
    if not picture_url:
        return None
    try:
        response = requests.get(picture_url, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return None
    return ContentFile(response.content, name="google_profile.jpg")


def get_or_create_user_from_google(idinfo):
    email = idinfo["email"]

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": email},
    )

    profile, profile_created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": idinfo.get("name", ""),
            "is_email_verified": True,
        },
    )

    if profile_created:
        image_file = _fetch_google_profile_image(idinfo.get("picture"))
        if image_file:
            profile.profile_image.save(image_file.name, image_file, save=True)
    elif not profile.is_email_verified:
        profile.is_email_verified = True
        profile.save(update_fields=["is_email_verified"])

    return user, created


def get_config_int(key, default):
    """Reads a tunable int from SystemConfig, falling back to `default` until someone sets it in admin."""
    cached = cache.get(key)
    if cached is not None:
        return int(cached)

    config = SystemConfig.objects.filter(name=key).first()
    value = config.value if config else str(default)
    cache.set(key, value, timeout=SYSTEM_CONFIG_CACHE_TTL)
    return int(value)


def get_global_auth_version():
    return get_config_int("global_auth_version", default=1)


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh["token_version"] = user.profile.token_version
    refresh["global_version"] = get_global_auth_version()
    return {"access_token": str(refresh.access_token), "refresh_token": str(refresh)}


def token_versions_valid(payload, profile):
    return (
        payload.get("token_version") == profile.token_version
        and payload.get("global_version") == get_global_auth_version()
    )


def refresh_access_token(refresh_token):
    try:
        refresh = RefreshToken(refresh_token)
    except TokenError:
        raise AuthError("Invalid or expired refresh token.", status_code=401)

    try:
        profile = UserProfile.objects.get(user_id=refresh.payload.get("user_id"))
    except UserProfile.DoesNotExist:
        raise AuthError("Invalid or expired refresh token.", status_code=401)

    if not token_versions_valid(refresh.payload, profile):
        raise AuthError("Session has been invalidated. Please log in again.", status_code=401)

    return str(refresh.access_token)


def invalidate_user_sessions(user):
    """Logs the user out everywhere: any token issued before this call stops working."""
    UserProfile.objects.filter(user=user).update(token_version=F("token_version") + 1)


def _profile_image_url(request, profile):
    if not profile.profile_image:
        return None
    url = profile.profile_image.url
    return request.build_absolute_uri(url) if request else url


def auth_user_payload(user, request=None):
    name = user.profile.full_name or f"{user.first_name} {user.last_name}".strip()
    return {
        "id": user.id,
        "email": user.email,
        "name": name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_image": _profile_image_url(request, user.profile),
    }


def me_payload(user, request=None):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gender": user.profile.gender,
        "date_of_birth": user.profile.date_of_birth,
        "profile_image": _profile_image_url(request, user.profile),
    }


def update_me(user, first_name=None, last_name=None, gender=None, date_of_birth=None, profile_image=None):
    if all(value is None for value in (first_name, last_name, gender, date_of_birth, profile_image)):
        raise AuthError("No fields provided to update.", status_code=400)

    changed_fields = []
    if first_name is not None:
        user.first_name = first_name
        changed_fields.append("first_name")
    if last_name is not None:
        user.last_name = last_name
        changed_fields.append("last_name")
    if changed_fields:
        user.save(update_fields=changed_fields)

    profile = user.profile
    profile_changed_fields = []

    if gender is not None:
        if gender not in VALID_GENDERS:
            raise AuthError(
                f"Invalid gender. Must be one of: {', '.join(sorted(VALID_GENDERS))}.", status_code=400
            )
        profile.gender = gender
        profile_changed_fields.append("gender")

    if date_of_birth is not None:
        parsed_dob = parse_date(date_of_birth) if isinstance(date_of_birth, str) else date_of_birth
        if parsed_dob is None:
            raise AuthError("Invalid date_of_birth. Use YYYY-MM-DD format.", status_code=400)
        profile.date_of_birth = parsed_dob
        profile_changed_fields.append("date_of_birth")

    if profile_image is not None:
        profile.profile_image = profile_image
        profile_changed_fields.append("profile_image")

    if profile_changed_fields:
        profile.save(update_fields=profile_changed_fields)

    return user


def generate_otp_code():
    return f"{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"


def otp_request_allowed(email):
    window_seconds = get_config_int("otp_request_window_seconds", settings.OTP_REQUEST_WINDOW_SECONDS)
    max_requests = get_config_int("otp_max_requests_per_window", settings.OTP_MAX_REQUESTS_PER_WINDOW)
    window_start = timezone.now() - timedelta(seconds=window_seconds)
    recent_count = OTP.objects.filter(recipient=email, created_at__gte=window_start).count()
    return recent_count < max_requests


def otp_request_allowed_for_ip(client_ip):
    max_requests = get_config_int(
        "otp_ip_max_requests_per_window", settings.OTP_IP_MAX_REQUESTS_PER_WINDOW
    )
    window_seconds = get_config_int(
        "otp_ip_request_window_seconds", settings.OTP_IP_REQUEST_WINDOW_SECONDS
    )
    cache_key = f"otp_request_rl:{client_ip}"
    count = cache.get(cache_key, 0)
    if count >= max_requests:
        return False
    cache.set(cache_key, count + 1, timeout=window_seconds)
    return True


def create_otp(email):
    code = generate_otp_code()
    OTP.objects.create(
        channel="email",
        recipient=email,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    return code


def send_otp_email(email, code):
    minutes = settings.OTP_TTL_SECONDS // 60
    message = (
        "Hello,\n\n"
        "Your verification code is:\n\n"
        f"{code}\n"
        f"This code expires in {minutes} minutes.\n"
        "If you did not request this, ignore this email.\n\n"
        "Thanks,\n"
        "Arborn Team"
    )
    send_mail(
        subject="Your Arborn verification code",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def verify_otp(email, code):
    otp = OTP.objects.filter(recipient=email, consumed=False).order_by("-created_at").first()
    if not otp or otp.is_expired():
        raise AuthError("Code expired or not found. Request a new one.", status_code=400)
    if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        raise AuthError("Too many attempts. Request a new code.", status_code=429)
    if not check_password(code, otp.code_hash):
        otp.attempt_count += 1
        otp.save(update_fields=["attempt_count"])
        raise AuthError("Incorrect code.", status_code=400)

    otp.consumed = True
    otp.save(update_fields=["consumed"])


def get_or_create_user_by_email(email):
    user, created = User.objects.get_or_create(email=email, defaults={"username": email})
    if created:
        UserProfile.objects.create(user=user, is_email_verified=True)
    elif not user.profile.is_email_verified:
        user.profile.is_email_verified = True
        user.profile.save(update_fields=["is_email_verified"])
    return user, created
