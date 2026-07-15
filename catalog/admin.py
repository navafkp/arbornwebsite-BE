from django import forms
from django.contrib import admin
from utils.admin_common import DuplicateAdminMixin
from utils.common_utils import SIZE_LABELS
from utils.catalog_duplicators import catalog_duplicator
from .models import (
    Category, Product, ProductFamily, ProductTag,
    ProductVariant, Review, Tag, VariantImage,Size
)


class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1
    fields = ["image", "display_order", "is_primary", "metadata"]


class ProductTagInline(admin.TabularInline):
    model = ProductTag
    extra = 1
    autocomplete_fields = ["tag"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "display_order"]
    prepopulated_fields = {"slug": ("name",)}
    fields = ["name", "slug", "image", "description", "display_order", "is_active", "metadata"]


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_active"]
    list_filter = ["category", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    fields = ["category", "name", "slug", "is_active", "metadata"]


@admin.register(Tag)
class TagAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = ["name", "slug", "display_order", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    duplicate_success_message = "Tag duplicated."
    fields = ["name", "slug", "image", "description", "display_order", "is_active", "metadata"]

    def duplicate_object(self, tag):
        return catalog_duplicator.duplicate_tag(tag)


@admin.register(Product)
class ProductAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = ["name", "product_family", "base_price", "is_active", "created_at"]
    list_filter = ["product_family__category", "is_active"]
    search_fields = ["name", "slug", "short_description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["recommended_products"]
    inlines = [ProductTagInline]
    duplicate_success_message = "Product duplicated."
    fields = [
        "product_family", "name", "slug", "short_description", "description",
        "base_price", "base_discount_price", "recommended_products", "is_active", "metadata",
    ]

    def duplicate_object(self, product):
        return catalog_duplicator.duplicate_product(product)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["size_label", "display_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code"]
    fields = ["code", "display_order", "measurement", "is_active", "metadata"]

    @admin.display(description="Size")
    def size_label(self, obj):
        return SIZE_LABELS.get(obj.code, obj.code)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "code":
            kwargs["widget"] = forms.Select(choices=list(SIZE_LABELS.items()))
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(ProductVariant)
class ProductVariantAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = ["product", "color", "min_supported_size", "max_supported_size", "price", "stock_quantity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["product__name", "sku"]
    inlines = [VariantImageInline]
    duplicate_success_message = "Product variant duplicated."
    fields = [
        "product", "color", "color_code", "min_supported_size", "max_supported_size",
        "price", "discount_price", "stock_quantity", "sku", "display_order", "is_active", "metadata",
    ]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("min_supported_size", "max_supported_size"):
            kwargs["widget"] = forms.Select(choices=list(SIZE_LABELS.items()))
        elif db_field.name == "color_code":
            kwargs["widget"] = forms.TextInput(attrs={"type": "color"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def duplicate_object(self, variant):
        return catalog_duplicator.duplicate_variant(variant)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user_profile", "rating", "title", "is_active", "created_at"]
    list_filter = ["rating", "is_active"]
    search_fields = ["product__name", "title", "review"]
    fields = ["product", "user_profile", "rating", "title", "review", "is_active"]


# Custom admin ordering
CATALOG_MODEL_ORDER = ["Category", "ProductFamily", "Product", "ProductVariant", "Review", "Tag", "Size"]
_default_get_app_list = admin.AdminSite.get_app_list


def _catalog_ordered_get_app_list(self, request, app_label=None):
    app_list = _default_get_app_list(self, request, app_label=app_label)
    for app in app_list:
        if app["app_label"] == "catalog":
            app["models"].sort(
                key=lambda m: CATALOG_MODEL_ORDER.index(m["object_name"])
                if m["object_name"] in CATALOG_MODEL_ORDER
                else len(CATALOG_MODEL_ORDER)
            )
    return app_list


admin.site.get_app_list = _catalog_ordered_get_app_list.__get__(admin.site, admin.AdminSite)
