from django.urls import path

from .views import HomeContentView, SelectSizeContentView

urlpatterns = [
    path("content/home/", HomeContentView.as_view(), name="content-home"),
    path("content/select-size/", SelectSizeContentView.as_view(), name="content-select-size"),
]
