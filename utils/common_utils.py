from django.db import transaction

def generate_sku():
    from catalog.models import ProductVariant
    with transaction.atomic():
        last_variant = ProductVariant.objects.select_for_update().order_by("-id").first()
        next_number = 1 if last_variant is None else last_variant.id + 1
    return f"ARB-{next_number:06d}"

SIZE_LABELS = {1: "M",2: "L",3: "XL",4: "XXL",5: "XXXL",6: "XXXXL"}

GENDER_CHOICES = [("male", "Male"),("female", "Female"),("other", "Other")]