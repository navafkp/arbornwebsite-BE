from django.db import transaction

def generate_sku():
    from catalog.models import VariantSizeStock
    with transaction.atomic():
        last_stock = VariantSizeStock.objects.select_for_update().order_by("-id").first()
        next_number = 1 if last_stock is None else last_stock.id + 1
    return f"ARB-{next_number:06d}"

SIZE_LABELS = {1: "M",2: "L",3: "XL",4: "XXL",5: "XXXL",6: "XXXXL",7: "Free Size"}

GENDER_CHOICES = [("male", "Male"),("female", "Female"),("other", "Other")]