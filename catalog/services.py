from django.db.models import Avg, Count, Min, Q
from django.db.models.functions import Coalesce

from utils.common_utils import SIZE_LABELS
from .models import Cart, Category, Order, Product, Review, Size, Tag, VariantImage, VariantSizeStock, Wishlist


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


PLUS_SIZE_CODES = [6, 8, 9]  # XXXXL, 5XL, 7XL


def get_size_list():
    # Individual sizes M through XXXL — Free Size (7) is handled separately per-product.
    sizes = [
        {
            "size_code": size.code,
            "display_text": SIZE_LABELS.get(size.code, str(size.code)),
            "measurement": size.measurement,
            "codes": [size.code],
        }
        for size in Size.objects.filter(is_active=True, code__lte=5)
        if size.metadata.get("is_show_on_explorer", True)
    ]
    # "Plus Size" is a filter grouping, not a real Size row — FE sends all of `codes`
    # together (e.g. ?size=5,6,8,9) when this option is picked, same as any other size.
    sizes.append({
        "size_code": "plus_size",
        "display_text": "PLUS SIZE",
        "measurement": "",
        "codes": PLUS_SIZE_CODES,
    })
    return sizes


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
    return [
        _category_like_payload(base_url, c) for c in Category.objects.filter(is_active=True)
        if c.metadata.get("is_show_on_explorer", True)
    ]


def get_tag_list(base_url=None):
    return [
        _category_like_payload(base_url, t) for t in Tag.objects.filter(is_active=True)
        if t.metadata.get("is_show_on_explorer", True)
    ]


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


def _variant_colors_payload(product):
    """Every active, in-stock variant's color, as a flat list — lets the UI render color swatches for this product."""
    return [
        color_code for color_code in
        product.variants.filter(is_active=True, size_stocks__is_active=True, size_stocks__stock_quantity__gt=0)
        .distinct().order_by("display_order").values_list("color_code", flat=True)
        if color_code
    ]


def _available_sizes_payload(product):
    """Every distinct in-stock size's display label across this product's active variants.
    A Free Size stock row (code 7) is expanded to the variant's actual min/max supported size range."""
    codes = set()
    stocks = VariantSizeStock.objects.filter(
        variant__product=product, variant__is_active=True, is_active=True, stock_quantity__gt=0
    ).select_related("variant", "size")
    for stock in stocks:
        if stock.size.code == 7:
            # 7 itself is the "Free Size" marker, not a real body size — exclude it even
            # if the variant's range technically spans across it (e.g. min=5, max=9).
            codes.update(
                code for code in range(stock.variant.min_supported_size, stock.variant.max_supported_size + 1)
                if code != 7
            )
        else:
            codes.add(stock.size.code)
    return [SIZE_LABELS.get(code, str(code)) for code in sorted(codes)]


def _related_product_images_payload(base_url, product):
    """Images of in-stock sibling products in the same family, excluding this one.
    Uses each sibling's thumbnail image, falling back to a variant image if no thumbnail is set."""
    siblings = Product.objects.filter(
        product_family_id=product.product_family_id, is_active=True,
        variants__is_active=True, variants__size_stocks__is_active=True,
        variants__size_stocks__stock_quantity__gt=0,
    ).exclude(id=product.id).distinct()
    images = [
        _image_url(base_url, s.thumbnail_image) or _primary_image_url(base_url, s)
        for s in siblings
    ]
    return [img for img in images if img]


def _product_list_item_payload(base_url, product):
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "base_price": product.computed_base_price,
        "base_discount_price": product.computed_base_discount_price,
        "image_url": _primary_image_url(base_url, product),
        "thumbnail_image": _image_url(base_url, product.thumbnail_image),
        "tag": _top_tag_payload(product),
        "colors": _variant_colors_payload(product),
        "sizes": _available_sizes_payload(product),
        "related_product_images": _related_product_images_payload(base_url, product),
    }


def _annotate_prices(qs):
    """Card price is always the cheapest active variant's price, computed on the fly instead
    of a stored Product.base_price — avoids it drifting out of sync with variant prices."""
    return qs.annotate(
        computed_base_price=Min("variants__price", filter=Q(variants__is_active=True)),
        computed_base_discount_price=Min(
            "variants__discount_price",
            filter=Q(variants__is_active=True, variants__discount_price__gt=0),
        ),
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


def list_products(
    sizes=None, category_slug=None, tag_slug=None, base_url=None, limit=None, page=None, page_size=None, search=None,
    sort=None, price_min=None, price_max=None,
):
    qs = _base_product_queryset().annotate(
        # The price a customer actually pays — discount price if set, else base price.
        effective_price=Coalesce("computed_base_discount_price", "computed_base_price")
    )

    if sizes:
        qs = qs.filter(Q(variants__is_active=True) & _sizes_match_q(sizes, prefix="variants__"))

    if category_slug:
        qs = qs.filter(product_family__category__slug=category_slug)

    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    if search:
        search = search.strip()
        search_q = (
            Q(name__icontains=search)
            | Q(short_description__icontains=search)
            | Q(product_family__category__name__icontains=search)
            | Q(tags__name__icontains=search)
        )
        # Size isn't free text anywhere — "Free Size" (or "M", "XL", ...) only exists as
        # SIZE_LABELS against a code on VariantSizeStock, so match the label back to its
        # code and search stock rows directly.
        size_code = next((code for code, label in SIZE_LABELS.items() if label.lower() == search.lower()), None)
        if size_code is not None:
            search_q |= Q(variants__size_stocks__size__code=size_code, variants__size_stocks__is_active=True)
        qs = qs.filter(search_q)

    if price_min is not None:
        qs = qs.filter(effective_price__gte=price_min)
    if price_max is not None:
        qs = qs.filter(effective_price__lte=price_max)

    if sort == "low-high":
        qs = qs.distinct().order_by("effective_price", "id")
    elif sort == "high-low":
        qs = qs.distinct().order_by("-effective_price", "id")
    else:
        qs = qs.distinct().order_by("id")

    if page is not None:
        page_size = page_size or 12
        total_count = qs.count()
        start = (page - 1) * page_size
        items = qs[start:start + page_size]
        return {
            "items": [_product_list_item_payload(base_url, p) for p in items],
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_next": start + page_size < total_count,
        }

    if limit is not None:
        qs = qs[:limit]
    return [_product_list_item_payload(base_url, p) for p in qs]


def _variant_sizes_payload(variant, sizes=None):
    """Per-size stock, sourced from VariantSizeStock — one row per size the variant actually stocks.
    A Free Size stock row (code 7) is expanded into one entry per size in the variant's
    min/max supported range, instead of showing "Free Size" as a single entry."""
    stocks = variant.size_stocks.filter(is_active=True, size__is_active=True).select_related("size").order_by("id")
    if sizes:
        size_filter = Q()
        for size in sizes:
            q = Q(size__code=size)
            if variant.min_supported_size <= size <= variant.max_supported_size:
                q |= Q(size__code=7)
            size_filter |= q
        stocks = stocks.filter(size_filter)

    size_measurements = {s.code: s.measurement for s in Size.objects.filter(is_active=True)}

    # Keyed by size_code so a duplicate (e.g. admin adding the same size twice, or a
    # Free Size range overlapping a direct size row) collapses to one entry — since `stocks`
    # is ordered oldest-first, whichever row is processed last (the newest) wins.
    by_size_code = {}
    for stock in stocks:
        if stock.size.code == 7:
            # 7 itself is the "Free Size" marker, not a real body size — exclude it even
            # if the variant's range technically spans across it (e.g. min=5, max=9).
            codes = [code for code in range(variant.min_supported_size, variant.max_supported_size + 1) if code != 7]
            if sizes:
                codes = [code for code in codes if code in sizes]
            free_size_note = _free_size_display_text(variant)
            for code in codes:
                by_size_code[code] = {
                    "variant_size_stock_id": stock.id,
                    "size_code": code,
                    "display_text": SIZE_LABELS.get(code, str(code)),
                    "measurement": size_measurements.get(code, ""),
                    "stock_quantity": stock.stock_quantity,
                    "is_free_size": True,
                    "free_size_note": free_size_note,
                }
        else:
            by_size_code[stock.size.code] = {
                "variant_size_stock_id": stock.id,
                "size_code": stock.size.code,
                "display_text": SIZE_LABELS.get(stock.size.code, str(stock.size.code)),
                "measurement": stock.size.measurement,
                "stock_quantity": stock.stock_quantity,
                "is_free_size": False,
                "free_size_note": None,
            }
    return sorted(by_size_code.values(), key=lambda s: s["size_code"])


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
        "discount_price": variant.discount_price if variant.discount_price and variant.discount_price > 0 else None,
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
        "verification_status": review.verification_status,
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

    review, created = Review.objects.update_or_create(
        product=product,
        user_profile=user_profile,
        defaults={"rating": rating, "title": title, "review": review_text},
    )
    if created:
        review.verification_status = "pending"
        review.save(update_fields=["verification_status"])
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
        "thumbnail_image": _image_url(base_url, product.thumbnail_image),
        "instagram_reel_url": product.instagram_reel_url or None,
        "instagram_thumbnail_url": _image_url(base_url, product.instagram_thumbnail_url),
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
            _variant_payload(base_url, v)
            for v in product.variants.filter(is_active=True, size_stocks__is_active=True).distinct()
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
                "product__variants__discount_price",
                filter=Q(product__variants__is_active=True, product__variants__discount_price__gt=0),
            ),
        )
    )
    payloads = []
    for item in items:
        item.product.computed_base_price = item.computed_base_price
        item.product.computed_base_discount_price = item.computed_base_discount_price
        payloads.append(_wishlist_item_payload(base_url, item.product))
    return payloads


def _variant_primary_image_url(base_url, variant):
    image = variant.images.order_by("-is_primary", "display_order").first()
    return _image_url(base_url, image.image) if image else None


def _free_size_display_text(variant):
    """A Free Size stock row covers a range of real sizes off one shared pool —
    say so explicitly, so the cart doesn't look like a single specific size."""
    min_label = SIZE_LABELS.get(variant.min_supported_size, str(variant.min_supported_size))
    max_label = SIZE_LABELS.get(variant.max_supported_size, str(variant.max_supported_size))
    return f"Free Size (Suitable for {min_label}-{max_label})"


def _cart_item_payload(base_url, cart_item):
    stock = cart_item.variant_size_stock
    variant = stock.variant
    product = variant.product
    price = variant.discount_price or variant.price
    size_display_text = (
        _free_size_display_text(variant) if stock.size.code == 7
        else SIZE_LABELS.get(stock.size.code, str(stock.size.code))
    )
    return {
        "id": cart_item.id,
        "product": {"id": product.id, "name": product.name, "slug": product.slug},
        "variant_id": variant.id,
        "color": variant.color,
        "color_code": variant.color_code,
        "size_code": stock.size.code,
        "size_display_text": size_display_text,
        "image_url": _variant_primary_image_url(base_url, variant),
        "price": price,
        "quantity": cart_item.quantity,
        "subtotal": price * cart_item.quantity,
        "stock_quantity": stock.stock_quantity,
        "is_out_of_stock": stock.stock_quantity <= 0,
        "is_stock_insufficient": cart_item.quantity > stock.stock_quantity,
    }


def get_cart(user_profile, base_url=None):
    items = Cart.objects.filter(user_profile=user_profile).select_related(
        "variant_size_stock__size", "variant_size_stock__variant__product"
    ).prefetch_related("variant_size_stock__variant__images")
    payloads = [_cart_item_payload(base_url, item) for item in items]
    return {
        "items": payloads,
        "total_quantity": sum(p["quantity"] for p in payloads),
        "total_amount": sum(p["subtotal"] for p in payloads),
    }


def add_to_cart(user_profile, variant_size_stock_id, quantity=1, base_url=None):
    """Returns None if variant_size_stock_id doesn't match a real, active stock row.
    Returns {"error": ...} if the requested quantity exceeds available stock."""
    try:
        stock = VariantSizeStock.objects.select_related("variant__product", "size").get(
            id=variant_size_stock_id, is_active=True, variant__is_active=True
        )
    except VariantSizeStock.DoesNotExist:
        return None

    existing_item = Cart.objects.filter(user_profile=user_profile, variant_size_stock=stock).first()
    new_quantity = (existing_item.quantity if existing_item else 0) + quantity

    if new_quantity > stock.stock_quantity:
        return {"error": f"Only {stock.stock_quantity} items available."}

    if existing_item is None:
        cart_item = Cart.objects.create(
            user_profile=user_profile, variant_size_stock=stock, quantity=new_quantity
        )
    else:
        existing_item.quantity = new_quantity
        existing_item.save(update_fields=["quantity"])
        cart_item = existing_item
    return _cart_item_payload(base_url, cart_item)


def update_cart_item(user_profile, cart_item_id, quantity, base_url=None):
    """Returns None if that cart item doesn't belong to this user.
    Returns {"error": ...} if the requested quantity exceeds available stock."""
    try:
        cart_item = Cart.objects.select_related(
            "variant_size_stock__variant__product", "variant_size_stock__size"
        ).get(id=cart_item_id, user_profile=user_profile)
    except Cart.DoesNotExist:
        return None

    if quantity > cart_item.variant_size_stock.stock_quantity:
        return {"error": f"Only {cart_item.variant_size_stock.stock_quantity} items available."}

    cart_item.quantity = quantity
    cart_item.save(update_fields=["quantity"])
    return _cart_item_payload(base_url, cart_item)


def remove_from_cart(user_profile, cart_item_id):
    """Returns False if that item wasn't in the user's cart."""
    deleted, _ = Cart.objects.filter(id=cart_item_id, user_profile=user_profile).delete()
    return deleted > 0


def remove_cart_items(user_profile, item_ids):
    """Returns how many of the given ids were actually in this user's cart."""
    deleted, _ = Cart.objects.filter(id__in=item_ids, user_profile=user_profile).delete()
    return deleted


def _order_item_payload(base_url, item):
    stock = item.variant_size_stock
    variant = stock.variant
    product = variant.product
    return {
        "id": item.id,
        "product": {"id": product.id, "name": product.name, "slug": product.slug},
        "variant_id": variant.id,
        "color": variant.color,
        "color_code": variant.color_code,
        "size_code": stock.size.code,
        "size_display_text": SIZE_LABELS.get(stock.size.code, str(stock.size.code)),
        "image_url": _variant_primary_image_url(base_url, variant),
        "quantity": item.quantity,
    }


def _order_payload(base_url, order):
    return {
        "id": order.id,
        "collected_amount": order.collected_amount,
        "shipping_charge": order.shipping_charge,
        "transport_mode": order.transport_mode,
        "state": order.state,
        "created_at": order.created_at,
        "items": [_order_item_payload(base_url, item) for item in order.items.all()],
    }


def get_orders(user_profile, base_url=None):
    orders = Order.objects.filter(user_profile=user_profile).prefetch_related(
        "items__variant_size_stock__size",
        "items__variant_size_stock__variant__product",
        "items__variant_size_stock__variant__images",
    ).order_by("-created_at")
    return [_order_payload(base_url, order) for order in orders]
