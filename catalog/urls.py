from django.urls import path
from .views import (
    category_list,
    explore,
    product_detail,
    product_list,
    product_review_create,
    size_list,
    tag_list,
    wishlist,
    wishlist_remove,
)

urlpatterns = [
    # version 1
    path("v1/sizes/", size_list, name="size-list"),
    path("v1/categories/", category_list, name="category-list"),
    path("v1/tags/", tag_list, name="tag-list"),
    path("v1/explore/", explore, name="explore"),
    path("v1/products/", product_list, name="product-list"),
    path("v1/products/<str:slug>/", product_detail, name="product-detail"),
    path("v1/products/<str:slug>/reviews/", product_review_create, name="product-review-create"),
    path("v1/wishlist/", wishlist, name="wishlist"),
    path("v1/wishlist/<int:product_id>/", wishlist_remove, name="wishlist-remove"),
]
