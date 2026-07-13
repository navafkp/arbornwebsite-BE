import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EmailOTP, User


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


def backfill_google_identity(user, google_sub, picture):
    """A user who first signed up via OTP gets their Google identity attached."""
    changed = False
    if not user.google_sub:
        user.google_sub = google_sub
        changed = True
    if not user.is_verified:
        user.is_verified = True
        changed = True
    if changed:
        user.save(update_fields=["google_sub", "is_verified"])

    if not user.profile.profile_image and picture:
        user.profile.profile_image = picture
        user.profile.save(update_fields=["profile_image"])


def get_or_create_user_from_google(idinfo):
    email = idinfo["email"]
    google_sub = idinfo["sub"]

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"google_sub": google_sub, "is_verified": True},
    )

    if created:
        user.profile.name = idinfo.get("name", "")
        user.profile.profile_image = idinfo.get("picture", "")
        user.profile.save(update_fields=["name", "profile_image"])
    else:
        backfill_google_identity(user, google_sub, idinfo.get("picture", ""))

    return user


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


def auth_user_payload(user):
    name = user.profile.name or f"{user.first_name} {user.last_name}".strip()
    return {
        "id": user.id,
        "email": user.email,
        "name": name,
        "profile_image": user.profile.profile_image,
    }


def me_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_image": user.profile.profile_image,
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
    recent_count = EmailOTP.objects.filter(email=email, created_at__gte=window_start).count()
    return recent_count < settings.OTP_MAX_REQUESTS_PER_WINDOW


def create_otp(email):
    code = generate_otp_code()
    EmailOTP.objects.create(
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
    otp = EmailOTP.objects.filter(email=email, consumed=False).order_by("-created_at").first()
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
    user, created = User.objects.get_or_create(email=email, defaults={"is_verified": True})
    if not created and not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
    return user
