from django.db import models
from django.utils.text import slugify
from django_resized import ResizedImageField
from utils.models import ActivatableModel, TimeStampedModel
from utils.common_utils import generate_sku


class Category(ActivatableModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = ResizedImageField(upload_to="categories/",force_format="WEBP",quality=90)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# recommendation josn----------------------------------------------------------------- for each product to show in ui
class ProductFamily(ActivatableModel, TimeStampedModel):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="product_families"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "product families"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(ActivatableModel, TimeStampedModel):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    image = ResizedImageField(upload_to="tags/",force_format="WEBP",quality=90)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "tags"
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(ActivatableModel, TimeStampedModel):
    product_family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    base_discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    tags = models.ManyToManyField(Tag, through="ProductTag", related_name="products")
    recommended_products = models.ManyToManyField("self",symmetrical=False,blank=True,related_name="recommended_by")
    
    class Meta:
        verbose_name_plural = "products"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductTag(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "tag"],
                name="unique_product_tag"
            )
        ]

class ProductVariant(TimeStampedModel, ActivatableModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=50, blank=True)
    min_supported_size = models.PositiveSmallIntegerField()
    max_supported_size = models.PositiveSmallIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = generate_sku(self)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "product variants"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color", "size"],
                name="unique_product_variant"
            )
        ]



class VariantImage(TimeStampedModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = ResizedImageField(upload_to="variants/",force_format="WEBP",quality=90)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "variant images"
        ordering = ["display_order", "id"]



class Review(TimeStampedModel, ActivatableModel):
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, related_name="reviews")
    user_profile = models.ForeignKey(
        "accounts.UserProfile", on_delete=models.DO_NOTHING, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255, blank=True)
    review = models.TextField()

    class Meta:
        verbose_name_plural = "reviews"
