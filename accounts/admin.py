from django import forms
from django.contrib import admin
from .models import UserProfile
from utils.common_utils import GENDER_CHOICES


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "phone", "is_account_blocked", "created_at"]
    list_filter = ["is_account_blocked"]
    search_fields = ["user__username", "user__email", "full_name", "phone"]
    fields = ["is_account_blocked", "is_email_verified", "user", "full_name", "phone", "profile_image", "date_of_birth", "gender"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "gender":
            kwargs["widget"] = forms.Select(choices=[("", "---------")] + list(GENDER_CHOICES))
        return super().formfield_for_dbfield(db_field, request, **kwargs)
