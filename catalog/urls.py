from django.urls import path
from .views import category_list, explore, product_list, size_list, tag_list

urlpatterns = [
    # version 1
    path("v1/sizes/", size_list, name="size-list"),
    path("v1/categories/", category_list, name="category-list"),
    path("v1/tags/", tag_list, name="tag-list"),
    path("v1/explore/", explore, name="explore"),
    path("v1/products/", product_list, name="product-list"),
]
