from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django_resized import ResizedImageField
from django.contrib.auth.models import User
from utils.models import ActivatableModel, TimeStampedModel

SYSTEM_CONFIG_CACHE_TTL = 60 * 60 * 24 * 14  # 14 days - safety net only; saves sync the cache instantly below


class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="profile")
    full_name = models.CharField(max_length=150,blank=True)
    phone = models.CharField(max_length=32,blank=True)
    profile_image = ResizedImageField(upload_to="users/",force_format="WEBP",quality=90, blank=True)
    date_of_birth = models.DateField(blank=True,null=True)
    gender = models.CharField(max_length=20,blank=True)
    is_account_blocked = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    token_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class SystemConfig(TimeStampedModel, ActivatableModel):
    """Runtime-editable key/value config — change a value here instead of redeploying."""

    name = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255,blank=True)
    metadata = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return self.name


@receiver(post_save, sender=SystemConfig)
def _sync_system_config_cache(sender, instance, **kwargs):
    cache.set(instance.name, instance.value, timeout=SYSTEM_CONFIG_CACHE_TTL)


@receiver(post_delete, sender=SystemConfig)
def _clear_system_config_cache(sender, instance, **kwargs):
    cache.delete(instance.name)


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

    def is_expired(self):
        return self.expires_at < timezone.now()
