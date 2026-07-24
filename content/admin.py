from django.contrib import admin

from .models import Banner, Story, StoryGroup


class StoryInline(admin.TabularInline):
    model = Story
    extra = 1
    fields = ["image", "eyebrow", "caption", "display_order", "duration_ms", "cta_label", "cta_link", "is_active"]


@admin.register(StoryGroup)
class StoryGroupAdmin(admin.ModelAdmin):
    list_display = ["label", "display_order", "is_active", "created_at", "updated_at"]
    inlines = [StoryInline]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["label", "cover_image", "display_order", "is_active", "created_at", "updated_at"]


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["alt_text", "display_order", "is_active", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "image", "alt_text", "display_order", "duration_ms", "link", "is_active",
        "created_at", "updated_at",
    ]
