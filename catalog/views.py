from config.decorators import api_endpoint, api_response, get_base_url, parse_json_body
from . import services


@api_endpoint(allowed_methods=["GET"], auth="none")
def size_list(request):
    return api_response(200, "Sizes fetched successfully", data=services.get_size_list())


@api_endpoint(allowed_methods=["GET"], auth="none")
def category_list(request):
    return api_response(
        200, "Categories fetched successfully", data=services.get_category_list(get_base_url(request))
    )


@api_endpoint(allowed_methods=["GET"], auth="none")
def tag_list(request):
    return api_response(
        200, "Tags fetched successfully", data=services.get_tag_list(get_base_url(request))
    )


@api_endpoint(allowed_methods=["GET"], auth="none")
def explore(request):
    return api_response(
        200, "Explore data fetched successfully", data=services.get_explore_payload(get_base_url(request))
    )


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_list(request):
    size_params = request.GET.getlist("size")
    sizes = []
    for s in size_params:
        for part in str(s).split(","):
            part = part.strip()
            if part:
                try:
                    sizes.append(int(part))
                except ValueError:
                    return api_response(400, "Invalid size.")

    category_slug = request.GET.get("category")
    tag_slug = request.GET.get("tag")

    limit = request.GET.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except ValueError:
            return api_response(400, "Invalid limit.")

    page = request.GET.get("page")
    if page is not None:
        try:
            page = int(page)
        except ValueError:
            return api_response(400, "Invalid page.")
        if page < 1:
            return api_response(400, "Invalid page.")

    page_size = request.GET.get("page_size")
    if page_size is not None:
        try:
            page_size = int(page_size)
        except ValueError:
            return api_response(400, "Invalid page_size.")
        if page_size < 1:
            return api_response(400, "Invalid page_size.")

    payload = services.list_products(
        sizes=sizes if sizes else None, category_slug=category_slug, tag_slug=tag_slug,
        base_url=get_base_url(request), limit=limit, page=page, page_size=page_size,
    )
    return api_response(200, "Products fetched successfully", data=payload)


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_detail(request, slug):
    size_params = request.GET.getlist("size")
    sizes = []
    for s in size_params:
        for part in str(s).split(","):
            part = part.strip()
            if part:
                try:
                    sizes.append(int(part))
                except ValueError:
                    return api_response(400, "Invalid size.")

    payload = services.get_product_detail(slug, base_url=get_base_url(request), sizes=sizes if sizes else None)
    if payload is None:
        return api_response(404, "Product not found.")
    return api_response(200, "Product fetched successfully", data=payload)


@api_endpoint(allowed_methods=["GET", "POST"], auth="user_authentication")
def wishlist(request):
    if request.method == "POST":
        data = parse_json_body(request)
        product_id = data.get("product_id")
        if not product_id:
            return api_response(400, "product_id is required.")

        added = services.add_to_wishlist(request.user.profile, product_id)
        if added is None:
            return api_response(404, "Product not found.")
        return api_response(200, "Added to wishlist.")

    payload = services.get_wishlist(request.user.profile, get_base_url(request))
    return api_response(200, "Wishlist fetched successfully", data=payload)


@api_endpoint(allowed_methods=["DELETE"], auth="user_authentication")
def wishlist_remove(request, product_id):
    removed = services.remove_from_wishlist(request.user.profile, product_id)
    if not removed:
        return api_response(404, "Item not found in wishlist.")
    return api_response(200, "Removed from wishlist.")


@api_endpoint(allowed_methods=["POST"], auth="user_authentication")
def product_review_create(request, slug):
    data = parse_json_body(request)

    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        return api_response(400, "rating must be an integer between 1 and 5.")
    if not 1 <= rating <= 5:
        return api_response(400, "rating must be an integer between 1 and 5.")

    review_text = data.get("review")
    if not review_text:
        return api_response(400, "review is required.")

    payload = services.create_review(
        request.user.profile, slug, rating, review_text, title=data.get("title", "")
    )
    if payload is None:
        return api_response(404, "Product not found.")
    return api_response(200, "Review submitted successfully.", data=payload)
