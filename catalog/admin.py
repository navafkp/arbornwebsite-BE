from django.contrib import admin

from .models import Category, Product, ProductFamily, ProductTag, ProductVariant, Review, Tag, VariantImage


class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1


class ProductVariantInline(admin.StackedInline):
    model = ProductVariant
    extra = 1


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "product_family", "base_price", "is_active", "created_at"]
    list_filter = ["product_family__category", "is_active"]
    search_fields = ["name", "slug", "short_description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductTagInline, ReviewInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["product", "color", "size", "price", "stock_quantity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["product__name", "sku"]
    inlines = [VariantImageInline]
