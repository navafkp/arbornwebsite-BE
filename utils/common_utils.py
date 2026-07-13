from django.db import transaction

def generate_sku():
    from catalog.models import ProductVariant

    last_variant = (
        ProductVariant.objects
        .select_for_update()
        .order_by("-id")
        .first()
    )

    next_number = 1 if last_variant is None else last_variant.id + 1

    return f"ARB-{next_number:06d}"