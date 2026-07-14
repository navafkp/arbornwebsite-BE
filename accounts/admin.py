from django import forms
from django.contrib import admin
from .models import OTP, SystemConfig, UserProfile
from .services import invalidate_user_sessions
from utils.common_utils import GENDER_CHOICES


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Read-only: OTPs are auto-generated, never meant to be manually created or edited."""

    list_display = ["recipient", "channel", "consumed", "attempt_count", "expires_at", "created_at"]
    list_filter = ["channel", "consumed"]
    search_fields = ["recipient"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "value", "updated_at"]
    search_fields = ["name"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "phone", "is_account_blocked", "created_at"]
    list_filter = ["is_account_blocked"]
    search_fields = ["user__username", "user__email", "full_name", "phone"]
    fields = ["is_account_blocked", "is_email_verified", "user", "full_name", "phone", "profile_image", "date_of_birth", "gender", "token_version"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "gender":
            kwargs["widget"] = forms.Select(choices=[("", "---------")] + list(GENDER_CHOICES))
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        newly_blocked = change and obj.is_account_blocked and "is_account_blocked" in form.changed_data
        super().save_model(request, obj, form, change)
        if newly_blocked:
            invalidate_user_sessions(obj.user)
