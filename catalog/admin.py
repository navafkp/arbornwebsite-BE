from django import forms
from django.contrib import admin
from utils.admin_common import DuplicateAdminMixin
from utils.common_utils import SIZE_LABELS,TRANSPORT_MODE_CHOICES
from utils.catalog_duplicators import catalog_duplicator
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import (
    Cart, Category, Order, OrderItem, Product, ProductFamily, ProductTag,
    ProductVariant, Review, Tag, VariantImage,Size, Wishlist,VariantSizeStock,
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
    list_display = ["name", "slug", "display_order", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "name", "slug", "image", "description", "display_order", "is_active", "metadata",
        "created_at", "updated_at",
    ]


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_active", "created_at", "updated_at"]
    list_filter = ["category", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]
    fields = ["category", "name", "slug", "is_active", "metadata", "created_at", "updated_at"]


@admin.register(Tag)
class TagAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = ["name", "slug", "display_order", "is_active", "created_at", "updated_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    duplicate_success_message = "Tag duplicated."
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "name", "slug", "image", "description", "display_order", "is_active", "metadata",
        "created_at", "updated_at",
    ]

    def duplicate_object(self, tag):
        return catalog_duplicator.duplicate_tag(tag)


@admin.register(Product)
class ProductAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = ["name", "product_family", "is_active", "created_at", "updated_at"]
    list_filter = ["product_family__category", "is_active"]
    search_fields = ["name", "slug", "short_description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["recommended_products"]
    inlines = [ProductTagInline]
    duplicate_success_message = "Product duplicated."
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "product_family", "name", "slug", "short_description", "description", "thumbnail_image",
        "instagram_reel_url", "instagram_thumbnail_url",
        "recommended_products", "is_active", "metadata", "created_at", "updated_at",
    ]

    def duplicate_object(self, product):
        return catalog_duplicator.duplicate_product(product)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["size_label", "display_order", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["code"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["code", "display_order", "measurement", "is_active", "metadata", "created_at", "updated_at"]

    @admin.display(description="Size")
    def size_label(self, obj):
        return SIZE_LABELS.get(obj.code, obj.code)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "code":
            kwargs["widget"] = forms.Select(choices=list(SIZE_LABELS.items()))
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(ProductVariant)
class ProductVariantAdmin(DuplicateAdminMixin, admin.ModelAdmin):
    list_display = [
        "product", "color", "min_supported_size", "max_supported_size", "price", "is_active",
        "created_at", "updated_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["product__name", "size_stocks__sku"]
    inlines = [VariantImageInline]
    duplicate_success_message = "Product variant duplicated."
    readonly_fields = ["created_at", "updated_at"]
    fields = [
        "product", "color", "color_code", "min_supported_size", "max_supported_size",
        "price", "discount_price", "display_order", "is_active", "metadata",
        "created_at", "updated_at",
    ]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("min_supported_size", "max_supported_size"):
            codes = [
                size.code for size in Size.objects.filter(is_active=True)
                if size.metadata.get("is_show_in_size_range", True)
            ]
            kwargs["widget"] = forms.Select(choices=[(code, SIZE_LABELS.get(code, str(code))) for code in codes])
        elif db_field.name == "color_code":
            kwargs["widget"] = forms.TextInput(attrs={"type": "color"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def duplicate_object(self, variant):
        return catalog_duplicator.duplicate_variant(variant)


@admin.register(VariantSizeStock)
class VariantSizeStockAdmin(admin.ModelAdmin):
    list_display = ["variant", "size", "stock_quantity", "sku", "is_active", "created_at", "updated_at"]
    list_filter = ["variant__product__name", "size", "is_active"]
    search_fields = ["variant__product__name", "sku"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["variant", "size", "stock_quantity", "sku", "is_active", "created_at", "updated_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user_profile", "rating", "title", "is_active", "created_at", "updated_at"]
    list_filter = ["rating", "is_active"]
    search_fields = ["product__name", "title", "review"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["product", "user_profile", "rating", "title", "review", "is_active", "created_at", "updated_at"]


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Read-only: wishlist entries are user actions, not something admins hand-author."""

    list_display = ["user_profile", "product", "created_at", "updated_at"]
    search_fields = ["user_profile__user__email", "product__name"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Read-only: cart entries are user actions, not something admins hand-author."""

    list_display = ["user_profile", "variant_size_stock", "quantity", "created_at", "updated_at"]
    search_fields = ["user_profile__user__email", "variant_size_stock__variant__product__name"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OrderItemInlineForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            return cleaned_data

        variant_stock = cleaned_data.get("variant_size_stock")
        quantity = cleaned_data.get("quantity")

        if not variant_stock or quantity is None:
            return cleaned_data

        if quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")
            return cleaned_data

        if self.instance.pk:
            old_item = OrderItem.objects.get(pk=self.instance.pk)

            if old_item.variant_size_stock_id != variant_stock.id:
                required_quantity = quantity
            else:
                required_quantity = quantity - old_item.quantity

                if required_quantity <= 0:
                    return cleaned_data
        else:
            required_quantity = quantity

        if variant_stock.stock_quantity < required_quantity:
            self.add_error("quantity", f"Only {variant_stock.stock_quantity} items available.")

        return cleaned_data


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemInlineForm
    extra = 1
    fields = ["variant_size_stock", "quantity"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["customer_name", "phone", "user_profile", "state", "collected_amount", "shipping_charge", "transport_mode", "notes", "created_at", "updated_at"]
    list_filter = ["state", "transport_mode"]
    search_fields = ["customer_name", "phone"]
    autocomplete_fields = ["user_profile"]
    inlines = [OrderItemInline]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["user_profile", "customer_name", "phone", "state", "collected_amount", "shipping_charge", "transport_mode", "notes", "is_active", "created_at", "updated_at"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "transport_mode":
            kwargs["widget"] = forms.Select(choices=TRANSPORT_MODE_CHOICES)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for order in queryset:
                for item in order.items.all():
                    item.variant_size_stock.stock_quantity += item.quantity
                    item.variant_size_stock.save(update_fields=["stock_quantity"])
            queryset.delete()

    def delete_model(self, request, obj):
        with transaction.atomic():
            for item in obj.items.all():
                item.variant_size_stock.stock_quantity += item.quantity
                item.variant_size_stock.save(update_fields=["stock_quantity"])
            super().delete_model(request, obj)

    def save_formset(self, request, form, formset, change):
        if formset.model is not OrderItem:
            return super().save_formset(request, form, formset, change)

        with transaction.atomic():
            # save(commit=False) is what actually performs deletions (Django deletes
            # marked-for-deletion rows immediately regardless of commit) and populates
            # deleted_objects — so it must run before either is used.
            instances = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.variant_size_stock.stock_quantity += obj.quantity
                obj.variant_size_stock.save(update_fields=["stock_quantity"])

            for instance in instances:
                if instance.pk:
                    old_item = OrderItem.objects.get(pk=instance.pk)

                    if old_item.variant_size_stock_id == instance.variant_size_stock_id:
                        difference = instance.quantity - old_item.quantity

                        if difference > 0:
                            if instance.variant_size_stock.stock_quantity < difference:
                                raise ValidationError(
                                    f"Only {instance.variant_size_stock.stock_quantity} items available."
                                )
                            instance.variant_size_stock.stock_quantity -= difference
                        elif difference < 0:
                            instance.variant_size_stock.stock_quantity += abs(difference)

                        instance.variant_size_stock.save(update_fields=["stock_quantity"])
                    else:
                        old_item.variant_size_stock.stock_quantity += old_item.quantity
                        old_item.variant_size_stock.save(update_fields=["stock_quantity"])

                        if instance.variant_size_stock.stock_quantity < instance.quantity:
                            raise ValidationError(
                                f"Only {instance.variant_size_stock.stock_quantity} items available."
                            )
                        instance.variant_size_stock.stock_quantity -= instance.quantity
                        instance.variant_size_stock.save(update_fields=["stock_quantity"])
                else:
                    if instance.variant_size_stock.stock_quantity < instance.quantity:
                        raise ValidationError(
                            f"Only {instance.variant_size_stock.stock_quantity} items available."
                        )
                    instance.variant_size_stock.stock_quantity -= instance.quantity
                    instance.variant_size_stock.save(update_fields=["stock_quantity"])

                instance.save()

            formset.save_m2m()

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
