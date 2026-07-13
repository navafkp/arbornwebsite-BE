from django.urls import path

from .views import google_auth, logout, me, otp_request, otp_verify, refresh_token

urlpatterns = [
    path("v1/auth/google", google_auth, name="auth-google"),
    path("v1/auth/refresh", refresh_token, name="auth-refresh"),
    path("v1/auth/logout", logout, name="auth-logout"),
    path("v1/auth/otp/request", otp_request, name="auth-otp-request"),
    path("v1/auth/otp/verify", otp_verify, name="auth-otp-verify"),
    path("v1/users/me", me, name="users-me"),
]
