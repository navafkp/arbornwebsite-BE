from django.http import JsonResponse
from config.decorators import api_endpoint
from . import services


@api_endpoint(allowed_methods=["GET"], auth="none")
def size_list(request):
    return JsonResponse(services.get_size_list(), safe=False)
