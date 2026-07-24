from django.urls import path

from .views import banner_list, story_list

urlpatterns = [
    path("v1/stories/", story_list, name="content-stories"),
    path("v1/banners/", banner_list, name="content-banners"),
]
