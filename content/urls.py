from django.urls import path

from .views import story_list

urlpatterns = [
    path("v1/stories/", story_list, name="content-stories"),
]
