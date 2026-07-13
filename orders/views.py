# from rest_framework import generics, permissions

# from .models import Order
# from .serializers import OrderSerializer


# class OrderListView(generics.ListAPIView):
#     """GET /api/orders/ — powers the profile photo grid."""

#     serializer_class = OrderSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     pagination_class = None

#     def get_queryset(self):
#         return (
#             Order.objects.filter(user=self.request.user)
#             .prefetch_related("items__product")
#         )


# class OrderDetailView(generics.RetrieveAPIView):
#     """GET /api/orders/{id}/ — powers the order-detail modal."""

#     serializer_class = OrderSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Order.objects.filter(user=self.request.user).prefetch_related("items__product")
