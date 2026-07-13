from django.db import models
# from django.utils import timezone
from django_resized import ResizedImageField
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="profile")
    full_name = models.CharField(max_length=150,blank=True)
    phone = models.CharField(max_length=32,blank=True)
    profile_image = ResizedImageField(upload_to="users/",force_format="WEBP",quality=90, blank=True)
    date_of_birth = models.DateField(blank=True,null=True)
    gender = models.CharField(max_length=20,blank=True)
    is_account_blocked = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class OTP(models.Model):
    channel = models.CharField(max_length=10)
    recipient = models.CharField(max_length=255)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
