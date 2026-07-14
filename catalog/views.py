from config.decorators import api_endpoint, api_response
from . import services


@api_endpoint(allowed_methods=["GET"], auth="none")
def size_list(request):
    return api_response(200, "Sizes fetched successfully", data=services.get_size_list())
