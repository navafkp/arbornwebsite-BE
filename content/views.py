from rest_framework import permissions
from rest_framework.generics import RetrieveAPIView

from .models import HomeContent, SelectSizeContent
from .serializers import HomeContentSerializer, SelectSizeContentSerializer


class HomeContentView(RetrieveAPIView):
    serializer_class = HomeContentSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return HomeContent.load()


class SelectSizeContentView(RetrieveAPIView):
    serializer_class = SelectSizeContentSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return SelectSizeContent.load()
