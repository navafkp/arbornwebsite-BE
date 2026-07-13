from rest_framework import serializers

from catalog.models import ProductVariant

from .models import HomeContent, SelectSizeContent


class HomeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeContent
        fields = ["headline", "subheadline", "hero_image", "cta_label", "cta_href"]


class SelectSizeContentSerializer(serializers.ModelSerializer):
    sizes = serializers.SerializerMethodField()

    class Meta:
        model = SelectSizeContent
        fields = [
            "heading",
            "subheading",
            "illustration_image",
            "sizes",
            "size_tip_text",
            "whatsapp_help_text",
            "important_note",
        ]

    def get_sizes(self, obj):
        # Sizes now live directly on ProductVariant (no separate lookup table).
        return list(
            ProductVariant.objects.filter(is_active=True)
            .exclude(size="")
            .values_list("size", flat=True)
            .distinct()
        )
