from utils.common_utils import SIZE_LABELS
from .models import Category, Product, Size, Tag, VariantImage


def get_size_list():
    return [
        {"size_code": size.code, "display_text": SIZE_LABELS.get(size.code, str(size.code))}
        for size in Size.objects.filter(is_active=True)
    ]


def _image_url(base_url, image_field):
    if not image_field:
        return None
    url = image_field.url
    return f"{base_url}{url}" if base_url else url


def _category_like_payload(base_url, obj):
    """Categories and tags render the same way in the UI, so they share this exact shape."""
    return {
        "id": obj.id,
        "name": obj.name,
        "slug": obj.slug,
        "image_url": _image_url(base_url, obj.image),
        "description": obj.description,
        "display_order": obj.display_order,
        "metadata": obj.metadata,
    }


def get_category_list(base_url=None):
    return [_category_like_payload(base_url, c) for c in Category.objects.filter(is_active=True)]


def get_tag_list(base_url=None):
    return [_category_like_payload(base_url, t) for t in Tag.objects.filter(is_active=True)]


def get_explore_payload(base_url=None):
    return {
        "categories": get_category_list(base_url),
        "tags": get_tag_list(base_url),
    }


def _primary_image_url(base_url, product):
    image = (
        VariantImage.objects.filter(variant__product=product)
        .order_by("-is_primary", "variant_id", "display_order")
        .first()
    )
    return _image_url(base_url, image.image) if image else None


def _product_list_item_payload(base_url, product):
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "image_url": _primary_image_url(base_url, product),
    }


def _base_product_queryset():
    return Product.objects.filter(is_active=True).select_related(
        "product_family", "product_family__category"
    )


def list_products(size=None, category_slug=None, tag_slug=None, base_url=None):
    qs = _base_product_queryset()

    if size is not None:
        qs = qs.filter(
            variants__is_active=True,
            variants__min_supported_size__lte=size,
            variants__max_supported_size__gte=size,
        )

    if category_slug:
        qs = qs.filter(product_family__category__slug=category_slug)

    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    qs = qs.distinct()
    return [_product_list_item_payload(base_url, p) for p in qs]
