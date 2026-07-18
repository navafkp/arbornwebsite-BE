from django.db.models import Avg, Count, Min, Q

from utils.common_utils import SIZE_LABELS
from .models import Category, Product, Review, Size, Tag, VariantImage, Wishlist


def _sizes_match_q(sizes, prefix=""):
    """A variant matches `sizes` if it stocks any of those sizes directly, or it has the Free Size stock
    (code=7) and its min/max supported range covers at least one of the requested sizes."""
    if not sizes:
        return Q()
    
    q_all = Q()
    for size in sizes:
        q_all |= Q(**{
            f"{prefix}size_stocks__is_active": True,
            f"{prefix}size_stocks__size__code": size,
        }) | Q(**{
            f"{prefix}size_stocks__is_active": True,
            f"{prefix}size_stocks__size__code": 7,
            f"{prefix}min_supported_size__lte": size,
            f"{prefix}max_supported_size__gte": size,
        })
    return q_all


def get_size_list():
    return [
        {
            "size_code": size.code,
            "display_text": SIZE_LABELS.get(size.code, str(size.code)),
            "measurement": size.measurement,
        }
        for size in Size.objects.filter(is_active=True)
        if size.metadata.get("is_show_on_explorer", True)
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
        "base_price": product.computed_base_price,
        "base_discount_price": product.computed_base_discount_price,
        "image_url": _primary_image_url(base_url, product),
        "tag": _top_tag_payload(product),
    }


def _annotate_prices(qs):
    """Card price is always the cheapest active variant's price, computed on the fly instead
    of a stored Product.base_price — avoids it drifting out of sync with variant prices."""
    return qs.annotate(
        computed_base_price=Min("variants__price", filter=Q(variants__is_active=True)),
        computed_base_discount_price=Min("variants__discount_price", filter=Q(variants__is_active=True)),
    )


def _base_product_queryset():
    return _annotate_prices(
        Product.objects.filter(
            is_active=True,
            variants__is_active=True,
            variants__size_stocks__is_active=True,
        ).select_related(
            "product_family", "product_family__category"
        )
    ).distinct()


def list_products(sizes=None, category_slug=None, tag_slug=None, base_url=None):
    qs = _base_product_queryset()

    if sizes:
        qs = qs.filter(Q(variants__is_active=True) & _sizes_match_q(sizes, prefix="variants__"))

    if category_slug:
        qs = qs.filter(product_family__category__slug=category_slug)

    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    qs = qs.distinct()
    return [_product_list_item_payload(base_url, p) for p in qs]


def _variant_sizes_payload(variant, sizes=None):
    """Per-size stock, sourced from VariantSizeStock — one row per size the variant actually stocks
    (a free-size variant just has a single row against the "Free Size" Size entry)."""
    stocks = variant.size_stocks.filter(is_active=True, size__is_active=True).select_related("size")
    if sizes:
        size_filter = Q()
        for size in sizes:
            q = Q(size__code=size)
            if variant.min_supported_size <= size <= variant.max_supported_size:
                q |= Q(size__code=7)
            size_filter |= q
        stocks = stocks.filter(size_filter)
    return [
        {
            "size_code": stock.size.code,
            "display_text": SIZE_LABELS.get(stock.size.code, str(stock.size.code)),
            "measurement": stock.size.measurement,
            "stock_quantity": stock.stock_quantity,
        }
        for stock in stocks
    ]


def _variant_image_payload(base_url, image):
    return {
        "id": image.id,
        "image_url": _image_url(base_url, image.image),
        "display_order": image.display_order,
        "is_primary": image.is_primary,
    }


def _variant_payload(base_url, variant, sizes=None):
    sizes_payload = _variant_sizes_payload(variant, sizes=sizes)
    return {
        "id": variant.id,
        "color": variant.color,
        "color_code": variant.color_code,
        "price": variant.price,
        "discount_price": variant.discount_price,
        "stock_quantity": sum(s["stock_quantity"] for s in sizes_payload),
        "sizes": sizes_payload,
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


def get_product_detail(slug, base_url=None, sizes=None):
    try:
        product = (
            _base_product_queryset()
            .prefetch_related("variants__images", "variants__size_stocks__size", "tags", "recommended_products")
            .get(slug=slug)
        )
    except Product.DoesNotExist:
        return None

    related_products = _base_product_queryset().filter(
        product_family=product.product_family
    ).exclude(id=product.id)
    if sizes:
        related_products = related_products.filter(_sizes_match_q(sizes, prefix="variants__")).distinct()

    reviews = product.reviews.filter(is_active=True).select_related("user_profile")

    variants = product.variants.filter(is_active=True, size_stocks__is_active=True).distinct()
    if sizes:
        variants = variants.filter(_sizes_match_q(sizes)).distinct()

    recommended_products = product.recommended_products.filter(
        is_active=True, variants__is_active=True, variants__size_stocks__is_active=True
    )
    if sizes:
        recommended_products = recommended_products.filter(_sizes_match_q(sizes, prefix="variants__"))
    recommended_products = _annotate_prices(recommended_products.distinct())

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "description": product.description,
        "base_price": product.computed_base_price,
        "base_discount_price": product.computed_base_discount_price,
        "category": {
            "id": product.product_family.category_id,
            "name": product.product_family.category.name,
            "slug": product.product_family.category.slug,
        },
        "tags": [tag.slug for tag in product.tags.all()],
        "variants": [_variant_payload(base_url, v, sizes=sizes) for v in variants],
        "recommended_products": [_product_list_item_payload(base_url, p) for p in recommended_products],
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
        "base_price": product.computed_base_price,
        "base_discount_price": product.computed_base_discount_price,
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
        .prefetch_related("product__variants__images", "product__variants__size_stocks__size", "product__tags")
        .annotate(
            computed_base_price=Min("product__variants__price", filter=Q(product__variants__is_active=True)),
            computed_base_discount_price=Min(
                "product__variants__discount_price", filter=Q(product__variants__is_active=True)
            ),
        )
    )
    payloads = []
    for item in items:
        item.product.computed_base_price = item.computed_base_price
        item.product.computed_base_discount_price = item.computed_base_discount_price
        payloads.append(_wishlist_item_payload(base_url, item.product))
    return payloads
