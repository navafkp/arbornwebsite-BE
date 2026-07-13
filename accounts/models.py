from django.db import models
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username



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
