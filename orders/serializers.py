# from rest_framework import serializers

# from .models import Order, OrderItem


# class OrderItemSerializer(serializers.ModelSerializer):
#     product_id = serializers.SerializerMethodField()
#     name = serializers.CharField(source="product_name")
#     image = serializers.URLField(source="image_url")

#     class Meta:
#         model = OrderItem
#         fields = ["product_id", "name", "image", "quantity", "price", "size"]

#     def get_product_id(self, obj):
#         return obj.product.slug if obj.product_id else ""


# class OrderSerializer(serializers.ModelSerializer):
#     items = OrderItemSerializer(many=True, read_only=True)
#     date = serializers.DateField(source="created_at", format="%Y-%m-%d")

#     class Meta:
#         model = Order
#         fields = ["id", "date", "status", "total", "items"]
