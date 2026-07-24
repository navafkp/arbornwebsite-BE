from .models import Banner, StoryGroup


def _image_url(base_url, image_field):
    if not image_field:
        return None
    url = image_field.url
    return f"{base_url}{url}" if base_url else url


def _story_payload(base_url, story):
    return {
        "id": story.id,
        "image_url": _image_url(base_url, story.image),
        "eyebrow": story.eyebrow,
        "caption": story.caption,
        "display_order": story.display_order,
        "duration_ms": story.duration_ms,
        "cta_label": story.cta_label or None,
        "cta_link": story.cta_link or None,
    }


def _story_group_payload(base_url, group):
    return {
        "id": group.id,
        "label": group.label,
        "cover_image_url": _image_url(base_url, group.cover_image),
        "display_order": group.display_order,
        "stories": [_story_payload(base_url, s) for s in group.stories.filter(is_active=True)],
    }


def get_story_groups(base_url=None):
    groups = StoryGroup.objects.filter(is_active=True).prefetch_related("stories")
    return [_story_group_payload(base_url, g) for g in groups]


def _banner_payload(base_url, banner):
    return {
        "id": banner.id,
        "image_url": _image_url(base_url, banner.image),
        "alt_text": banner.alt_text,
        "display_order": banner.display_order,
        "duration_ms": banner.duration_ms,
        "link": banner.link or None,
    }


def get_banners(base_url=None):
    banners = Banner.objects.filter(is_active=True)
    return [_banner_payload(base_url, b) for b in banners]
