from django.urls import path

from . import views

urlpatterns = [
    path("v1/categories", views.category_list, name="category-list"),
    path("v1/categories/<int:category_id>", views.category_detail, name="category-detail"),
    path("v1/tags", views.tag_list, name="tag-list"),
    path("v1/products", views.product_list, name="product-list"),
    path("v1/products/<int:product_id>", views.product_detail, name="product-detail"),
    path("v1/products/<int:product_id>/related", views.product_related, name="product-related"),
    path("v1/products/<int:product_id>/reviews", views.product_reviews, name="product-reviews"),
    path(
        "v1/products/<int:product_id>/recommendations",
        views.product_recommendations,
        name="product-recommendations",
    ),
    path("v1/search", views.search, name="search"),
    path("v1/home", views.home, name="home"),
    path("v1/explore", views.explore, name="explore"),
]
