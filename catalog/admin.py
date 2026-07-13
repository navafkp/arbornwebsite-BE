from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.crypto import get_random_string
from .models import (
    Category, Product, ProductFamily, ProductTag,
    ProductVariant, Review, Tag, VariantImage,Size
)
class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1
class ProductVariantInline(admin.StackedInline):
    model = ProductVariant
    extra = 1

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("min_supported_size", "max_supported_size"):
            kwargs["widget"] = forms.Select(choices=list(SIZE_LABELS.items()))
        return super().formfield_for_dbfield(db_field, request, **kwargs)

class ProductTagInline(admin.TabularInline):
    model = ProductTag
    extra = 1
class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["user_profile", "rating", "title", "review", "created_at"]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "display_order"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_active"]
    list_filter = ["category", "is_active"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "display_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}

def _duplicate_product(product):
    variants = list(product.variants.all())
    tag_links = list(ProductTag.objects.filter(product=product))

    product.pk = None
    product.id = None
    product.name = f"{product.name}-copy-{get_random_string(6).lower()}"
    product.slug = f"{product.slug}-copy-{get_random_string(6).lower()}"
    product.save()

    for tag_link in tag_links:
        ProductTag.objects.create(product=product, tag=tag_link.tag)

    for variant in variants:
        images = list(variant.images.all())
        variant.pk = None
        variant.id = None
        variant.product = product
        variant.sku = ""
        variant.save()
        for image in images:
            image.pk = None
            image.id = None
            image.variant = variant
            image.save()

    return product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "product_family", "base_price", "is_active", "created_at"]
    list_filter = ["product_family__category", "is_active"]
    search_fields = ["name", "slug", "short_description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["recommended_products"]
    change_form_template = "admin/catalog/product/change_form.html"
    # inlines = [ProductVariantInline, ProductTagInline, ReviewInline]

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/duplicate/",
                self.admin_site.admin_view(self.duplicate_view),
                name="catalog_product_duplicate",
            ),
        ]
        return custom_urls + super().get_urls()

    def duplicate_view(self, request, object_id):
        product = self.get_object(request, object_id)
        if product is None:
            messages.error(request, "Product not found.")
            return redirect("admin:catalog_product_changelist")

        new_product = _duplicate_product(product)
        messages.success(request, f'Duplicated "{product.name}" as "{new_product.name}".')
        return redirect("admin:catalog_product_change", new_product.pk)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["code", "display_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code"]

SIZE_LABELS = {
    1: "M",
    2: "L",
    3: "XL",
    4: "XXL",
    5: "XXXL",
    6: "XXXXL",
}


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["product", "color", "min_supported_size", "max_supported_size", "price", "stock_quantity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["product__name", "sku"]
    inlines = [VariantImageInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("min_supported_size", "max_supported_size"):
            kwargs["widget"] = forms.Select(choices=list(SIZE_LABELS.items()))
        return super().formfield_for_dbfield(db_field, request, **kwargs)


CATALOG_MODEL_ORDER = ["Category", "ProductFamily", "Product", "ProductVariant", "Tag", "Size"]
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
