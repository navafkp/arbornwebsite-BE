from config.decorators import api_endpoint, api_response, get_base_url
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
    size = request.GET.get("size")
    if size is not None:
        try:
            size = int(size)
        except ValueError:
            return api_response(400, "Invalid size.")

    category_slug = request.GET.get("category")
    tag_slug = request.GET.get("tag")

    payload = services.list_products(
        size=size, category_slug=category_slug, tag_slug=tag_slug, base_url=get_base_url(request)
    )
    return api_response(200, "Products fetched successfully", data=payload)
