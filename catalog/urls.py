from django.urls import path
from .views import size_list

urlpatterns = [
    # version 1
    path("v1/sizes/", size_list, name="size-list")
]
