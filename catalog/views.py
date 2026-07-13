from django.http import JsonResponse

from config.decorators import api_endpoint, check_user_auth, parse_json_body

from . import services


@api_endpoint(allowed_methods=["GET"], auth="none")
def category_list(request):
    return JsonResponse(services.get_category_list(), safe=False)


@api_endpoint(allowed_methods=["GET"], auth="none")
def category_detail(request, category_id):
    try:
        payload = services.get_category_detail(category_id)
    except services.ServiceError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)
    return JsonResponse(payload)


@api_endpoint(allowed_methods=["GET"], auth="none")
def tag_list(request):
    return JsonResponse(services.get_tag_list(), safe=False)


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_list(request):
    return JsonResponse(services.list_products(request))


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_detail(request, product_id):
    try:
        payload = services.get_product_detail(product_id)
    except services.ServiceError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)
    return JsonResponse(payload)


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_related(request, product_id):
    try:
        payload = services.get_related_products(product_id)
    except services.ServiceError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)
    return JsonResponse(payload, safe=False)


@api_endpoint(allowed_methods=["GET", "POST"], auth="none")
def product_reviews(request, product_id):
    if request.method == "POST":
        authenticated, message = check_user_auth(request)
        if not authenticated:
            return JsonResponse({"detail": message}, status=401)

        data = parse_json_body(request)
        try:
            payload = services.create_product_review(product_id, request.user, data)
        except services.ServiceError as exc:
            return JsonResponse({"detail": exc.message}, status=exc.status_code)
        return JsonResponse(payload, status=201)

    try:
        payload = services.get_product_reviews(request, product_id)
    except services.ServiceError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)
    return JsonResponse(payload)


@api_endpoint(allowed_methods=["GET"], auth="none")
def product_recommendations(request, product_id):
    try:
        payload = services.get_product_recommendations(product_id)
    except services.ServiceError as exc:
        return JsonResponse({"detail": exc.message}, status=exc.status_code)
    return JsonResponse(payload, safe=False)


@api_endpoint(allowed_methods=["GET"], auth="none")
def search(request):
    return JsonResponse(services.search_products(request))


@api_endpoint(allowed_methods=["GET"], auth="none")
def home(request):
    return JsonResponse(services.get_home_payload())


@api_endpoint(allowed_methods=["GET"], auth="none")
def explore(request):
    return JsonResponse(services.get_explore_payload())
