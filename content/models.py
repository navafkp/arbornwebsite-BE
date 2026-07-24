from django.db import models
from django_resized import ResizedImageField
from utils.models import ActivatableModel, TimeStampedModel


class StoryGroup(ActivatableModel, TimeStampedModel):
    label = models.CharField(max_length=100,blank=True)
    cover_image = ResizedImageField(upload_to="stories/covers/", force_format="WEBP", quality=90, blank=True, null=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.label
    
    class Meta:
        verbose_name_plural = "story groups"


class Story(ActivatableModel, TimeStampedModel):
    group = models.ForeignKey(StoryGroup, on_delete=models.CASCADE, related_name="stories")
    image = ResizedImageField(upload_to="stories/", force_format="WEBP", quality=90, blank=True, null=True)
    eyebrow = models.CharField(max_length=100, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=3000)
    cta_label = models.CharField(max_length=100, blank=True)
    cta_link = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.group.label} story #{self.display_order}"

    class Meta:
        verbose_name_plural = "stories"

class Banner(ActivatableModel, TimeStampedModel):
    image = ResizedImageField(upload_to="banners/", force_format="WEBP", quality=90,blank=True, null=True)
    alt_text = models.CharField(max_length=255,blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=5000)
    link = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.alt_text

    class Meta:
        verbose_name_plural = "banners"
