from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models



class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    phone = models.CharField(
        max_length=32,
        blank=True,
    )

    profile_image = models.URLField(
        blank=True,
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
    )

    is_blocked = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.user.username




# @receiver(post_save, sender=User)
# def create_profile_for_new_user(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.get_or_create(user=instance)


# class EmailOTP(models.Model):
#     """Short-lived one-time code for passwordless email login."""

#     email = models.EmailField(db_index=True)
#     code_hash = models.CharField(max_length=128)
#     expires_at = models.DateTimeField()
#     attempt_count = models.PositiveSmallIntegerField(default=0)
#     consumed = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-created_at"]

#     def is_expired(self):
#         return timezone.now() >= self.expires_at

#     def __str__(self):
#         return f"OTP for {self.email} ({'used' if self.consumed else 'pending'})"
