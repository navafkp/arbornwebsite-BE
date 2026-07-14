from django.urls import path

from . import views

urlpatterns = [
    path("v1/sizes", views.size_list, name="size-list")
]
