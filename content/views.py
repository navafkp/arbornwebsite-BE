from config.decorators import api_endpoint, api_response, get_base_url

from . import services


@api_endpoint(allowed_methods=["GET"], auth="none")
def story_list(request):
    return api_response(200, "Stories fetched successfully", data=services.get_story_groups(get_base_url(request)))
