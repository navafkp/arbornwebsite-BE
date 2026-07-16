from django.db.models import Avg, Count

from utils.common_utils import SIZE_LABELS
from .models import Category, Product, Review, Size, Tag, VariantImage, Wishlist


def get_size_list():
    return [
        {
            "size_code": size.code,
            "display_text": SIZE_LABELS.get(size.code, str(size.code)),
            "measurement": size.measurement,
        }
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


def _top_tag_payload(product):
    """A product can have several tags — show only the highest-priority one as the card badge."""
    tag = product.tags.filter(is_active=True).order_by("display_order").first()
    return {"name": tag.name, "slug": tag.slug} if tag else None


def _product_list_item_payload(base_url, product):
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "image_url": _primary_image_url(base_url, product),
        "tag": _top_tag_payload(product),
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


def _variant_sizes_payload(variant):
    """Same {size_code, display_text} shape as get_size_list() — FE sends size_code back to place an order."""
    sizes = Size.objects.filter(
        is_active=True,
        code__gte=variant.min_supported_size,
        code__lte=variant.max_supported_size,
    )
    return [
        {
            "size_code": size.code,
            "display_text": SIZE_LABELS.get(size.code, str(size.code)),
            "measurement": size.measurement,
        }
        for size in sizes
    ]


def _variant_image_payload(base_url, image):
    return {
        "id": image.id,
        "image_url": _image_url(base_url, image.image),
        "display_order": image.display_order,
        "is_primary": image.is_primary,
    }


def _variant_payload(base_url, variant):
    return {
        "id": variant.id,
        "color": variant.color,
        "color_code": variant.color_code,
        "price": variant.price,
        "discount_price": variant.discount_price,
        "stock_quantity": variant.stock_quantity,
        "sizes": _variant_sizes_payload(variant),
        "images": [_variant_image_payload(base_url, image) for image in variant.images.all()],
    }


def _review_payload(review):
    return {
        "id": review.id,
        "rating": review.rating,
        "title": review.title,
        "review": review.review,
        "reviewer_name": review.user_profile.full_name or "Anonymous",
        "created_at": review.created_at,
    }


def _review_summary_payload(product):
    """Just the rating — used wherever we don't want the full review list (e.g. wishlist)."""
    aggregate = product.reviews.filter(is_active=True).aggregate(
        average_rating=Avg("rating"), review_count=Count("id")
    )
    return {
        "average_rating": round(aggregate["average_rating"], 1) if aggregate["average_rating"] else 0,
        "review_count": aggregate["review_count"] or 0,
    }


def create_review(user_profile, slug, rating, review_text, title=""):
    """Returns None if the slug doesn't match a real, active product."""
    try:
        product = Product.objects.get(slug=slug, is_active=True)
    except Product.DoesNotExist:
        return None

    review, _ = Review.objects.update_or_create(
        product=product,
        user_profile=user_profile,
        defaults={"rating": rating, "title": title, "review": review_text},
    )
    return _review_payload(review)


def get_product_detail(slug, base_url=None):
    try:
        product = (
            _base_product_queryset()
            .prefetch_related("variants__images", "tags", "recommended_products")
            .get(slug=slug)
        )
    except Product.DoesNotExist:
        return None

    related_products = _base_product_queryset().filter(
        product_family=product.product_family
    ).exclude(id=product.id)

    reviews = product.reviews.filter(is_active=True).select_related("user_profile")

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "description": product.description,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "category": {
            "id": product.product_family.category_id,
            "name": product.product_family.category.name,
            "slug": product.product_family.category.slug,
        },
        "tags": [tag.slug for tag in product.tags.all()],
        "variants": [
            _variant_payload(base_url, v) for v in product.variants.filter(is_active=True)
        ],
        "recommended_products": [
            _product_list_item_payload(base_url, p)
            for p in product.recommended_products.filter(is_active=True)
        ],
        "related_products": [_product_list_item_payload(base_url, p) for p in related_products],
        "review_summary": _review_summary_payload(product),
        "reviews": [_review_payload(r) for r in reviews],
    }


def add_to_wishlist(user_profile, product_id):
    """Returns None if product_id doesn't match a real, active product."""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return None
    Wishlist.objects.get_or_create(user_profile=user_profile, product=product)
    return True


def remove_from_wishlist(user_profile, product_id):
    """Returns False if that product wasn't in the user's wishlist."""
    deleted, _ = Wishlist.objects.filter(
        user_profile=user_profile, product_id=product_id
    ).delete()
    return deleted > 0


def _wishlist_item_payload(base_url, product):
    """Richer than the plain list-item shape — user picks size/color and orders directly from wishlist."""
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "image_url": _primary_image_url(base_url, product),
        "tag": _top_tag_payload(product),
        "variants": [
            _variant_payload(base_url, v) for v in product.variants.filter(is_active=True)
        ],
        "review_summary": _review_summary_payload(product),
    }


def get_wishlist(user_profile, base_url=None):
    items = (
        Wishlist.objects.filter(user_profile=user_profile)
        .select_related("product", "product__product_family", "product__product_family__category")
        .prefetch_related("product__variants__images", "product__tags")
    )
    return [_wishlist_item_payload(base_url, item.product) for item in items]
