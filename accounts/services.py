import secrets
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP, UserProfile


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
    cache_key = f"google_auth_rl:{client_ip}"
    count = cache.get(cache_key, 0)
    if count >= settings.GOOGLE_AUTH_MAX_REQUESTS_PER_WINDOW:
        return False
    cache.set(cache_key, count + 1, timeout=settings.GOOGLE_AUTH_REQUEST_WINDOW_SECONDS)
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


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access_token": str(refresh.access_token), "refresh_token": str(refresh)}


def refresh_access_token(refresh_token):
    try:
        refresh = RefreshToken(refresh_token)
    except TokenError:
        raise AuthError("Invalid or expired refresh token.", status_code=401)
    return str(refresh.access_token)


def blacklist_refresh_token(refresh_token):
    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        raise AuthError("Invalid or expired refresh token.", status_code=400)


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
        "profile_image": _profile_image_url(request, user.profile),
    }


def update_me(user, first_name=None, last_name=None):
    changed_fields = []
    if first_name is not None:
        user.first_name = first_name
        changed_fields.append("first_name")
    if last_name is not None:
        user.last_name = last_name
        changed_fields.append("last_name")
    if changed_fields:
        user.save(update_fields=changed_fields)
    return user


def generate_otp_code():
    return f"{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"


def otp_request_allowed(email):
    window_start = timezone.now() - timedelta(seconds=settings.OTP_REQUEST_WINDOW_SECONDS)
    recent_count = OTP.objects.filter(email=email, created_at__gte=window_start).count()
    return recent_count < settings.OTP_MAX_REQUESTS_PER_WINDOW


def create_otp(email):
    code = generate_otp_code()
    OTP.objects.create(
        email=email,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    return code


def send_otp_email(email, code):
    send_mail(
        subject="Your Arborn verification code",
        message=f"Your code is {code}. It expires in {settings.OTP_TTL_SECONDS // 60} minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def verify_otp(email, code):
    otp = OTP.objects.filter(email=email, consumed=False).order_by("-created_at").first()
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
