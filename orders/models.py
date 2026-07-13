from django.conf import settings
from django.db import models


# class Order(models.Model):
#     class Status(models.TextChoices):
#         CONTACTED_WHATSAPP = "contacted_whatsapp", "Contacted via WhatsApp"
#         PROCESSING = "processing", "Processing"
#         SHIPPED = "shipped", "Shipped"
#         DELIVERED = "delivered", "Delivered"
#         CANCELLED = "cancelled", "Cancelled"

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
#     )
#     status = models.CharField(
#         max_length=20, choices=Status.choices, default=Status.CONTACTED_WHATSAPP
#     )
#     total = models.DecimalField(max_digits=9, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-created_at"]

#     def __str__(self):
#         return f"Order #{self.pk} — {self.user.email}"


# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     variant = models.ForeignKey(
#         "catalog.ProductVariant",
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="order_items",
#     )

#     # Snapshots at order time — if the variant's name, price, or photo
#     # changes later (or the variant is deleted), past orders must not
#     # silently change too.
#     product_name = models.CharField(max_length=200)
#     color_name = models.CharField(max_length=50)
#     size = models.CharField(max_length=8)
#     quantity = models.PositiveIntegerField(default=1)
#     price = models.DecimalField(max_digits=8, decimal_places=2)
#     image_url = models.URLField()

#     def __str__(self):
#         return f"{self.quantity}x {self.product_name} ({self.size})"
