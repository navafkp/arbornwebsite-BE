from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q

from content.models import HomeContent

from .models import Category, Product, Review, Tag, VariantImage

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 100
RECOMMENDATION_LIMIT = 12
HOME_SECTION_LIMIT = 8

SORT_OPTIONS = {
    "price_low": ("base_price",),
    "price_high": ("-base_price",),
    "newest": ("-created_at",),
}


class ServiceError(Exception):
    """Raised for any catalog failure that should become an error JSON response."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def paginate(request, queryset, default_page_size=DEFAULT_PAGE_SIZE):
    try:
        page_number = int(request.GET.get("page", 1))
    except ValueError:
        page_number = 1

    try:
        page_size = int(request.GET.get("page_size", default_page_size))
    except ValueError:
        page_size = default_page_size
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    meta = {
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
    }
    return page_obj, meta


# --- payload builders ----------------------------------------------------


def category_payload(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "image_url": category.image_url,
        "metadata": category.metadata,
    }


def tag_payload(tag):
    return {
        "id": tag.id,
        "name": tag.name,
        "image_url": tag.image_url,
    }


def _primary_image_url(product):
    image = (
        VariantImage.objects.filter(variant__product=product)
        .order_by("-is_primary", "variant_id", "display_order")
        .first()
    )
    return image.image_url if image else None


def product_list_item_payload(product):
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "image_url": _primary_image_url(product),
        "category_id": product.product_family.category_id,
        "family_id": product.product_family_id,
        "is_active": product.is_active,
    }


def variant_payload(variant):
    return {
        "id": variant.id,
        "color": variant.color,
        "size": variant.size,
        "price": variant.price,
        "discount_price": variant.discount_price,
        "stock_quantity": variant.stock_quantity,
        "sku": variant.sku,
        "is_active": variant.is_active,
        "images": [
            {
                "id": image.id,
                "image_url": image.image_url,
                "display_order": image.display_order,
                "is_primary": image.is_primary,
            }
            for image in variant.images.all()
        ],
    }


def review_summary_payload(product):
    summary = product.reviews.filter(is_active=True).aggregate(
        average_rating=Avg("rating"), review_count=Count("id")
    )
    return {
        "average_rating": round(summary["average_rating"], 1) if summary["average_rating"] else 0,
        "review_count": summary["review_count"] or 0,
    }


def product_detail_payload(product):
    variants = list(product.variants.prefetch_related("images").all())
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "short_description": product.short_description,
        "description": product.description,
        "base_price": product.base_price,
        "base_discount_price": product.base_discount_price,
        "is_active": product.is_active,
        "metadata": product.metadata,
        "family": {
            "id": product.product_family_id,
            "name": product.product_family.name,
            "slug": product.product_family.slug,
            "category": category_payload(product.product_family.category),
        },
        "tags": [tag_payload(tag) for tag in product.tags.all()],
        "variants": [variant_payload(variant) for variant in variants],
        "colors": sorted({v.color for v in variants if v.color}),
        "sizes": sorted({v.size for v in variants if v.size}),
        "review_summary": review_summary_payload(product),
    }


def review_payload(review):
    return {
        "id": review.id,
        "rating": review.rating,
        "title": review.title,
        "review": review.review,
        "reviewer_name": review.user_profile.name or "Anonymous",
        "created_at": review.created_at,
    }


# --- categories / tags -----------------------------------------------------


def get_category_list():
    return [category_payload(c) for c in Category.objects.all()]


def get_category_detail(category_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        raise ServiceError("Category not found.", status_code=404)
    return category_payload(category)


def get_tag_list():
    return [tag_payload(t) for t in Tag.objects.filter(is_active=True)]


# --- products ----------------------------------------------------------


def _base_product_queryset():
    return Product.objects.filter(is_active=True).select_related(
        "product_family", "product_family__category"
    )


def filter_products(request):
    qs = _base_product_queryset()

    category_id = request.GET.get("category_id")
    if category_id:
        qs = qs.filter(product_family__category_id=category_id)

    tag_id = request.GET.get("tag_id")
    if tag_id:
        qs = qs.filter(tags__id=tag_id)

    family_id = request.GET.get("family_id")
    if family_id:
        qs = qs.filter(product_family_id=family_id)

    search = request.GET.get("search")
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(short_description__icontains=search))

    sort = request.GET.get("sort")
    if sort == "popular":
        qs = qs.annotate(num_reviews=Count("reviews")).order_by("-num_reviews", "-created_at")
    else:
        qs = qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"]))

    return qs.distinct()


def list_products(request):
    qs = filter_products(request)
    page_obj, meta = paginate(request, qs)
    results = [product_list_item_payload(p) for p in page_obj.object_list]
    return {**meta, "results": results}


def get_product(product_id):
    try:
        return Product.objects.select_related(
            "product_family", "product_family__category"
        ).get(pk=product_id, is_active=True)
    except Product.DoesNotExist:
        raise ServiceError("Product not found.", status_code=404)


def get_product_detail(product_id):
    return product_detail_payload(get_product(product_id))


def get_related_products(product_id):
    product = get_product(product_id)
    related = _base_product_queryset().filter(
        product_family_id=product.product_family_id
    ).exclude(pk=product.id)
    return [product_list_item_payload(p) for p in related]


def get_product_reviews(request, product_id):
    get_product(product_id)  # 404 if missing
    qs = Review.objects.filter(product_id=product_id, is_active=True).select_related(
        "user_profile"
    )
    page_obj, meta = paginate(request, qs)
    results = [review_payload(r) for r in page_obj.object_list]
    return {**meta, "results": results}


def create_product_review(product_id, user, data):
    product = get_product(product_id)

    rating = data.get("rating")
    review_text = data.get("review")
    if rating is None or not review_text:
        raise ServiceError("rating and review are required.")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ServiceError("rating must be a number between 1 and 5.")
    if not 1 <= rating <= 5:
        raise ServiceError("rating must be between 1 and 5.")

    review = Review.objects.create(
        product=product,
        user_profile=user.profile,
        rating=rating,
        title=data.get("title", ""),
        review=review_text,
    )
    return review_payload(review)


def search_products(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return {"count": 0, "page": 1, "page_size": DEFAULT_PAGE_SIZE, "total_pages": 0, "results": []}

    qs = (
        _base_product_queryset()
        .filter(Q(name__icontains=query) | Q(short_description__icontains=query))
        .distinct()
    )
    page_obj, meta = paginate(request, qs)
    results = [product_list_item_payload(p) for p in page_obj.object_list]
    return {**meta, "results": results}


# --- aggregate pages -----------------------------------------------------


def get_home_payload():
    home_content = HomeContent.load()
    banners = [
        {
            "headline": home_content.headline,
            "subheadline": home_content.subheadline,
            "image_url": home_content.hero_image.url if home_content.hero_image else None,
            "cta_label": home_content.cta_label,
            "cta_href": home_content.cta_href,
        }
    ]

    featured = _base_product_queryset().filter(tags__slug="featured").distinct()[
        :HOME_SECTION_LIMIT
    ]
    best_sellers = _base_product_queryset().filter(tags__slug="best-sellers").distinct()[
        :HOME_SECTION_LIMIT
    ]
    new_arrivals = _base_product_queryset().order_by("-created_at")[:HOME_SECTION_LIMIT]

    return {
        "banners": banners,
        "categories": get_category_list(),
        "explore_tags": get_tag_list(),
        "featured_products": [product_list_item_payload(p) for p in featured],
        "new_arrivals": [product_list_item_payload(p) for p in new_arrivals],
        "best_sellers": [product_list_item_payload(p) for p in best_sellers],
    }


def get_explore_payload():
    return {
        "categories": get_category_list(),
        "tags": get_tag_list(),
    }


def get_product_recommendations(product_id):
    product = get_product(product_id)

    same_family = _base_product_queryset().filter(
        product_family_id=product.product_family_id
    ).exclude(pk=product.id)
    same_category = (
        _base_product_queryset()
        .filter(product_family__category_id=product.product_family.category_id)
        .exclude(pk=product.id)
    )
    best_sellers = (
        _base_product_queryset().filter(tags__slug="best-sellers").exclude(pk=product.id)
    )

    seen_ids = {product.id}
    recommendations = []
    for qs in (same_family, same_category, best_sellers):
        for candidate in qs.distinct():
            if candidate.id in seen_ids:
                continue
            seen_ids.add(candidate.id)
            recommendations.append(candidate)
            if len(recommendations) >= RECOMMENDATION_LIMIT:
                break
        if len(recommendations) >= RECOMMENDATION_LIMIT:
            break

    return [product_list_item_payload(p) for p in recommendations]
